import os
from google.genai import Client

def load_env():

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT","sixth-sequencer-419216")
    os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")
    os.environ.setdefault('DATABASE_ID','sixth-sequencer-419216.customer_dataset')

    print("environment varialble loaded!")

def get_client():
    load_env()
    client = Client(
      vertexai=True,
      project= os.environ.get("GOOGLE_CLOUD_PROJECT"),
      location=os.environ.get("GOOGLE_CLOUD_REGION"),)
    print("Client created successfully!")
    return client