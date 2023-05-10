#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import io
import os
import json
import pandas as pd
import requests
import boto3
from botocore.exceptions import ClientError

pd.set_option('display.max_columns', None)

# Yelp Data
api_key = os.environ['YELP_API_KEY']
url_y = 'https://api.yelp.com/v3/businesses/search'
# NYC Open Data
url_n = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

# Set AWS access and secret keys
ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
SECRET_KEY = os.environ['AWS_SECRET_KEY']
bucket_name = "finalpiplinedata"

def save_to_s3(dataframe, bucket_name, file_name):
    csv_string = dataframe.to_csv(index=False)
    # Create a connection to your AWS account
    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    # Upload files to the bucket
    s3_resource = boto3.resource('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    bucket = s3_resource.Bucket(bucket_name)
    bucket.put_object(Key=file_name, Body=csv_string.encode())


def get_yelp_data(url_y):
    all_restaurants = []
    headers = {'Authorization': 'Bearer %s' % api_key}
    params = {
        'term': 'restaurants',
        'location': 'Manhattan, NY',
        'categories': 'restaurants',
        'limit': 50,
    }
    
    # Loop through the maximum number of pages (1000 results / 50 results per page)
    for offset in range(0, 1000, 50):
        params['offset'] = offset
        response = requests.get(url_y, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            all_restaurants.extend(data['businesses'])
        else:
            print("Error: Unable to retrieve data")
            break

    yelp = pd.json_normalize(all_restaurants)
    #Keep 9 digital numbers only.
    yelp['phone'] = yelp['phone'].str.slice(2)
    yelp_data=yelp
    return yelp_data

def get_nyc_open_data(url_n):
    # Set a limit for the number of rows to fetch in each request
    limit = 20000

    # Initialize an empty list to store the data
    all_data = []

    # Start with an offset of 0
    offset = 0

    while True:
        # Add the limit and offset parameters to the API request
        response = requests.get(url_n, params={'$limit': limit, '$offset': offset})

        if response.status_code == 200:
            data = response.json()

            # Check if there's any data left to fetch
            if not data:
                break

            # Add the fetched data to the list
            all_data.extend(data)

            # Update the offset for the next request
            offset += limit
        else:
            print(f"Failed to fetch data (status code: {response.status_code})")
            break
    nyc = pd.DataFrame(all_data)
    # Only foucs on Manhattan restaurants
    nyc_data = nyc.loc[nyc['boro']=='Manhattan']
    return nyc_data

def lambda_handler(event, context):
    yelp_data = get_yelp_data(url_y)
    nyc_open_data = get_nyc_open_data(url_n)

    save_to_s3(yelp_data, "yelp_data.csv")
    save_to_s3(nyc_open_data, "nyc_open_data.csv")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Data saved to S3"})
    }

