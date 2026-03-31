import os
from google.genai import Client

def load_env():

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT","<project-name")
    os.environ.setdefault("GOOGLE_CLOUD_REGION", "<location>")
    os.environ.setdefault('DATABASE_ID','<project-name>.<ctable-name in big query>')

    print("environment varialble loaded!")

def get_client():
    load_env()
    client = Client(
      vertexai=True,
      project= os.environ.get("GOOGLE_CLOUD_PROJECT"),
      location=os.environ.get("GOOGLE_CLOUD_REGION"),)
    print("Client created successfully!")
    return client