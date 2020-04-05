# -*- coding: utf-8 -*-

"""Classes for S3 Buckets."""
import mimetypes
from botocore.exceptions import ClientError
from pathlib import Path


class BucketManager:
    """manage  an S3 bucket."""

    def __init__(self, session):
        """Create a bucket manager."""
        self.session = session
        self.s3 = self.session.resource('s3')

    def all_buckets(self):
        """Get an iterator for all buckets."""
        return self.s3.buckets.all()

    def all_objects(self, bucket):
        """get an iterator for all objects in bucket."""
        return self.s3.Bucket(bucket).objects.all()

    def init_bucket(self, bucket_name):
        """Create a new bucket with name provided."""
        try:
            s3_bucket = self.s3.create_bucket(  # pylint: disable=maybe-no-member
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': self.session.region_name
                }
            )
        except ClientError as error:
            if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = self.s3.Bucket(bucket_name) # pylint: disable=maybe-no-member
                print("%s is already owned by you." % bucket_name)
            else:
                raise error
        return s3_bucket

    @staticmethod
    def set_policy(s3_bucket):
        """Set bucket policy to be readable by everyone."""
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

    @staticmethod
    def configure_website(s3_bucket):
        """Configure bucket as static website."""
        s3_bucket.Website().put(WebsiteConfiguration={
            'ErrorDocument': {
                'Key': 'error.html'
            },
            'IndexDocument': {
                'Suffix': 'index.html'
            }
        })

    @staticmethod
    def upload_file(s3_bucket, path, key):
        """Upload a file or directory to s3 bucket."""
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'

        return s3_bucket.upload_file(
            path,
            key,
            ExtraArgs={
                'ContentType': content_type
            }
        )

    def sync(self, pathname, bucket_name):
        """Sync files and directories to s3 bucket."""
        bucket = self.s3.Bucket(bucket_name)
        root = Path(pathname).expanduser().resolve()

        def handle_directory(target):
            for path_found in target.iterdir():
                if path_found.is_dir():
                    handle_directory(path_found)
                if path_found.is_file():
                    self.upload_file(bucket,
                                     str(path_found),
                                     str(path_found.relative_to(root)
                                         )
                                     )

        handle_directory(root)
        print("Successfully synced %s to %s" % (pathname, bucket_name))
