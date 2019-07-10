import os
import boto3
import logging
import io
import re
import time

## pulled from Environment Varibales in Lambda -- default is: ERROR
log_level = os.environ['LOG_LEVEL']
log_level = log_level.upper()  ## set log level to upper case

##works with AWS Logger: https://stackoverflow.com/questions/10332748/python-logging-setlevel
logger = logging.getLogger()
level = logging.getLevelName(log_level)
logger.setLevel(level)


def list_metrics(client, request):
    try:
        check = client.list_metrics(**request)
        if (check['ResponseMetadata']['HTTPStatusCode'] == 200):
            result = {
                'Status': 'SUCCESS',
                'Response': check
            }



    except Exception as ex:
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)}
        }
    return result



def get_metrics(client, beginning, ending, request):
    try:
        check = client.get_metric_data(MetricDataQueries=request, StartTime=beginning, EndTime=ending)
        if (check['ResponseMetadata']['HTTPStatusCode'] == 200 and check['MetricDataResults'][0]['Values'] != []):
            result = {
                'Status': 'SUCCESS',
                'Response': check
            }
        else:
            result = {
                'Status': 'FAILED',
                'Reason': 'No Data',
                'Response': check
            }

    except Exception as ex:
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)}
        }
    return result


def format_data(metric_name, incoming_metrics, today, time_in_seconds):
    new_file = io.StringIO()
    for metric in incoming_metrics['Response']['MetricDataResults']:
        row = '''{"timestamp": "%s", "id": "%s", "emt_config": "%s", "metric_name": "%s", "period": %s, "value": %s}''' % \
        (today, metric['Id'], metric['Label'], metric_name, time_in_seconds, metric['Values'][0])
        new_file.write(row)
        new_file.write('\n')
    return new_file


def metric_layout_2(metric_values, namespace, metricname, time_period):
    channel_metric_request = []

    for i, metric in enumerate(metric_values['Response']['Metrics']):
        channel = metric['Dimensions'][0]['Value']
        if re.search('(p12\w)', channel):
            id_string = re.search('(p12\w)', channel, 1).group()
        else:
            id_string = "dev%s" % i

        test2 = {
            "Id": id_string.lower(),
            "MetricStat": {
                "Metric": {
                    "Namespace": namespace,
                    "MetricName": metricname,
                    "Dimensions": [
                        {
                            "Name": "ConfigurationName",
                            "Value": channel
                        }
                    ]
                },
                "Period": time_period,
                "Stat": "Sum",
                "Unit": "Milliseconds"
            }
        }
        channel_metric_request.append(test2)
    return channel_metric_request

def metric_layout_1(namespace, metricname):
    metric_1 = {
        "Namespace": namespace,
        "MetricName": metricname
    }
    return metric_1

def save_to_bucket(s3_r, bucket_name, filename, body_text):
    ## pulled from Environment Varibales in Lambda
    bucket = s3_r.Bucket(bucket_name)
    path = filename
    data = body_text.getvalue()

    bucket.put_object(
        ACL='private',
        ContentType='application/json',
        Key=path,
        Body=data,
    )
    result = check_file(bucket_name, filename)
    return result

def check_file(bucket, filename):
    s3_client = boto3.client('s3')
    try:
        check = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=filename
        )
        if (check['ResponseMetadata']['HTTPStatusCode'] == 200):
            result = {
                'Status': 'SUCCESS',
                'Response': check
            }

    except Exception as ex:
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)}
        }

    return result


def lambda_handler(event, context):

    namespace = "AWS/MediaTailor"
    metricname = "Avail.Duration"
    time_period = 86400
    bucket_name = os.environ['DESTINATION_BUCKET']


    cloudwatch = boto3.client('cloudwatch')
    s3 = boto3.resource('s3')

    metric = metric_layout_1(namespace, metricname)
    logger.debug("Lambda_Handler, metric: %s" % metric)

    # grab metric names, aka dimension name, value's, should be 7
    metric_values = list_metrics(cloudwatch, metric)
    logger.debug("Lambda_Handler, metric_values: %s" % metric_values)

    t = time.time()
    logger.debug("Time Now: %s" % t)
    yesterday = t - time_period
    start = time.strftime('%Y-%m-%dT00:00:00Z', time.gmtime(yesterday))
    end = time.strftime('%Y-%m-%dT23:59:59Z', time.gmtime(yesterday))
    logger.debug("Lambda_Handler, dates: %s, %s" % (start, end))

    channel_metric_request = metric_layout_2(metric_values, namespace, metricname, time_period)
    logger.debug("Lambda_Handler, channel_metric_request: %s" % channel_metric_request)

    metrics_data = get_metrics(cloudwatch, start, end, channel_metric_request)
    if metrics_data['Status'] == "FAILED":
        logger.error("Lambda_Handler, metrics_data: %s" % metrics_data)
    else:
        logger.info("Lambda_Handler, metrics_data: %s" % metrics_data)
        formatted_metrics = format_data(metricname, metrics_data, end, time_period)
        logger.debug("Lambda_Handler, formatted_metrics: \n%s" % formatted_metrics.getvalue())

        filename = "%s_emt_metrics.json" % (end)
        uploaded = save_to_bucket(s3, bucket_name, filename, formatted_metrics)
        logger.info("Lambda_Handler, uploaded: %s" % uploaded)