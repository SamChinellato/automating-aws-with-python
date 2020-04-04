#!usr/bin/python
# -*- coding: utf-8 -*-

"""Webotron: Deploy websites to AWS
Webotron automates the process of deploying static websites to AWS

- Configure and create aws buckets
- Set them up for static website hosting
- Configure DNS with Route 53
- Configure a CDN with Cloudfronts"""

import mimetypes
from pathlib import Path
import boto3
import click
from botocore.exceptions import ClientError

SESSION = boto3.Session(profile_name='personal', region_name='us-east-2')
S3 = SESSION.resource('s3')


@click.group()
def cli():
    """Webotron deploys websites to AWS"""


@cli.command('list-buckets')
def list_buckets():
    """List all s3 Buckets"""
    for bucket in S3.buckets.all():  # pylint: disable=maybe-no-member
        print(bucket)


@cli.command('list-bucket-objects')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in an s3 bucket"""
    for obj in S3.Bucket(bucket).objects.all():  # pylint: disable=maybe-no-member
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure an s3 bucket"""
    s3_bucket = None
    try:
        s3_bucket = S3.create_bucket(  # pylint: disable=maybe-no-member
            Bucket=bucket,
            CreateBucketConfiguration={
                'LocationConstraint': SESSION.region_name
            }
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            s3_bucket = S3.Bucket(bucket)  # pylint: disable=maybe-no-member
        else:
            raise error
    policy = """
    {
      "Version":"2012-10-17",
      "Statement":[{
      "Sid":"PublicReadGetObject",
      "Effect":"Allow",
      "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::%s/*"
          ]
        }
      ]
    }
    """ % s3_bucket.name
    policy = policy.strip()
    pol = s3_bucket.Policy()
    pol.put(Policy=policy)
    s3_bucket.Website().put(WebsiteConfiguration={
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    })


def upload_file(s3_bucket, path, key):
    """Upload a file or directory to s3 bucket"""
    content_type = mimetypes.guess_type(key)[0] or 'text/plain'
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': content_type
        }
    )


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET"""
    s3_bucket = S3.Bucket(bucket)  # pylint: disable=maybe-no-member
    root = Path(pathname).expanduser().resolve()

    def handle_directory(target):
        for path_found in target.iterdir():
            if path_found.is_dir():
                handle_directory(path_found)
            if path_found.is_file():
                upload_file(s3_bucket, str(path_found), str(path_found.relative_to(root)))

    handle_directory(root)


if __name__ == '__main__':
    cli()
