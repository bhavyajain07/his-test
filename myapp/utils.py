# utils.py
import boto3
import json
from botocore.exceptions import NoCredentialsError
from langchain.document_loaders import AmazonTextractPDFLoader
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.question_answering import load_qa_chain
from langchain_community.llms import OpenAI
import os
import traceback

class EmiratesIDProcessor:
    def __init__(self, **kwargs):
        # Initialize AWS clients with credentials from kwargs
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=kwargs.get('AWS_ACCESS_KEY'),
            aws_secret_access_key=kwargs.get('AWS_SECRET_KEY'),
            region_name=kwargs.get('AWS_REGION')
        )
        
        self.textract_client = boto3.client(
            'textract',
            aws_access_key_id=kwargs.get('AWS_ACCESS_KEY'),
            aws_secret_access_key=kwargs.get('AWS_SECRET_KEY'),
            region_name=kwargs.get('AWS_REGION')
        )
        
        self.bucket_name = kwargs.get('bucket_name')
        os.environ["OPENAI_API_KEY"] = kwargs.get('OPENAI_API_KEY')

    def upload_to_s3(self, file, filename, folder="cards"):
        try:
            if not file:
                raise ValueError("No file provided")

            s3_path = f"{folder}/{filename}"
            print(f"Attempting to upload to S3: {s3_path}")  # Debug print
            self.s3_client.upload_fileobj(file, self.bucket_name, s3_path)
            s3_uri = f"s3://{self.bucket_name}/{s3_path}"
            print(f"Successfully uploaded to S3: {s3_uri}")  # Debug print
            
            return s3_uri
        except Exception as e:
            print(f"S3 upload error details: {str(e)}")  # Detailed error
            raise Exception(f"S3 upload failed: {str(e)}")

    def process_and_query(self, text, query):
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=512, 
                chunk_overlap=32, 
                length_function=len
            )
            texts = text_splitter.split_text(text)
            embeddings = OpenAIEmbeddings()
            docsearch = FAISS.from_texts(texts, embeddings)
            chain = load_qa_chain(OpenAI(temperature=0), chain_type="stuff")  # Set temperature to 0 for more consistent output
            docs = docsearch.similarity_search(query)
            result = chain.run(input_documents=docs, question=query)
        
        # Clean and format the result
            try:
                # First attempt to parse as is
                # json.loads(result)
                return result
            except json.JSONDecodeError:
            # If parsing fails, try to clean and format the response
            # Remove any leading/trailing text that's not part of the JSON
                result = result.strip()
                start_idx = result.find('{')
                end_idx = result.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    result = result[start_idx:end_idx]
            
            # Ensure property names are properly quoted
                result = result.replace("'", '"')
            
            # Try to parse again
                try:
                    json.loads(result)  # Validate JSON
                    return result
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON after cleaning: {result}")
                # If still fails, return a structured JSON
                    default_response = {
                        "Full Name": "",
                        "Card ID Number": "",
                        "Date of Birth": "",
                        "Issue Date": "",
                        "Expiry Date": ""
                    }
                    return json.dumps(default_response)
                
        except Exception as e:
            print(f"Query processing error: {str(e)}")
            raise Exception(f"Query processing failed: {str(e)}")

    def process_card_side(self, file_path):
        try:
            loader = AmazonTextractPDFLoader(file_path, client=self.textract_client)
            documents = loader.load()
            return documents[0].page_content
        except Exception as e:
            print(f"Card processing error: {str(e)}")
            raise Exception(f"Card processing failed: {str(e)}")

    def extract_emirates_data(self, front_file, back_file):
        try:
            # Upload files to S3
            front_s3_path = self.upload_to_s3(front_file, f"front_{front_file.name}")
            print(f"Front S3 path: {front_s3_path}")
            back_s3_path = self.upload_to_s3(back_file, f"back_{back_file.name}")
            print(f"Back S3 path: {back_s3_path}")

            # Process front side
            print("Processing front side...")
            front_text = self.process_card_side(front_s3_path)
            print(f"Front text extracted: {front_text[:100]}...")

            front_query = """Extract the following information and return it in valid JSON format. 
            Return ONLY the JSON object, no additional text.
            Required format:
            {
                "Full Name": "extracted name",
                "Card ID Number": "extracted id",
                "Date of Birth": "DD/MM/YYYY", 
                "Issue Date": "DD/MM/YYYY",
                "Expiry Date": "DD/MM/YYYY"
            }"""

            print("Querying front text...")
            front_result = self.process_and_query(front_text, front_query)
            print(f"Front query result: {front_result}")

            # Process back side
            print("Processing back side...")
            back_text = self.process_card_side(back_s3_path)
            print(f"Back text extracted: {back_text[:100]}...")

            back_query = """Extract the following information and return it in valid JSON format.
            Return ONLY the JSON object, no additional text.
            Required format:
            {
                "Occupation": "extracted occupation",
                "Employer name": "extracted employer"
            }"""

            print("Querying back text...")
            back_result = self.process_and_query(back_text, back_query)
            print(f"Back query result: {back_result}")

            try:
                # Parse JSON results with error handling
                print("Attempting to parse front JSON...")
                front_data = json.loads(front_result.strip())
                print("Front JSON parsed successfully")

                print("Attempting to parse back JSON...")
                back_data = json.loads(back_result.strip())
                print("Back JSON parsed successfully")

            except json.JSONDecodeError as e:
                print(f"Front result: {front_result}")
                print(f"Back result: {back_result}")
                raise Exception(f"JSON parsing failed: {str(e)}")

            # Extract name components
            full_name = front_data.get('Full Name', '')
            names = full_name.split() if full_name else []
            print(f"Extracted name components: {names}")

            # Format dates to match HTML input format (YYYY-MM-DD)
            def format_date(date_str):
                if not date_str:
                    return ''
                try:
                    day, month, year = date_str.split('/')
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    return date_str

            extracted_data = {
                'first_name': names[0] if names else '',
                'middle_name': ' '.join(names[1:-1]) if len(names) > 2 else '',
                'last_name': names[-1] if len(names) > 1 else '',
                'id_number': front_data.get('Card ID Number', ''),
                'date_of_birth': format_date(front_data.get('Date of Birth', '')),
                'issue_date': format_date(front_data.get('Issue Date', '')),
                'expiry_date': format_date(front_data.get('Expiry Date', '')),
                'occupation': back_data.get('Occupation', ''),
                'employer': back_data.get('Employer name', '')
            }
            print(f"Final extracted data: {extracted_data}")
            return extracted_data

        except Exception as e:
            print(f"Processing error: {str(e)}")
            print(f"Full error traceback: {traceback.format_exc()}")
            raise Exception(f"Emirates ID processing failed: {str(e)}")