# emt_metrics

A basic tool to convert Elemental MediaTailor metrics into queryable logs in S3.

AWS Boto3 will need to be installed on your machine to run locally, however you can skip that if you're deploying direct to AWS.
AWS SAM is recommended deployment method, find more about that here: https://github.com/awslabs/aws-sam-cli

Sam offers easy deployment from a local machine into AWS using template files, which will be to be adjusted for your own needs before running this tool.

To Start: adjust the template file (template_.yaml) to suit your aws environment.  
The file has indications as to what text will need to replaced using greater Than, Less Than <> signs around a given word

Once those changes have been made, the following commands can be run using SAM:
This tool can be run locally by running the following commands:
`sam local invoke emtmetrics --no-event`

If you want to try it on AWS, use the following commands:
The following command builds it for deployment, zipping up the files into an s3 location
 - `sam package --template-file template_.yaml --s3-bucket <S3_BUCKET_NAME> --output-template-file packaged.yml`
This next command deploys it using cloudformation:
 - `sam deploy --template-file packaged.yml --stack-name <STACK NAME> --capabilities CAPABILITY_NAMED_IAM`

