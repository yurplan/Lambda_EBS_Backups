# Original code from:
# https://serverlesscode.com/post/lambda-schedule-ebs-snapshot-backups/
# http://blog.powerupcloud.com/2016/02/15/automate-ebs-snapshots-using-lambda-function/
# Rewritten to be configured on individual Volumes, not Instances.
# https://github.com/Brayyy/Lambda-EBS-Snapshot-Manager
# Updated for Python 3.6, added local time to 4/day, added requirement for EBS volume to be 'in-use'
# https://github.com/TacMechMonkey/Lambda_EBS_Backups-Python_3-6

import datetime
import time
import os

import boto3

RETENTION_DEFAULT = 90
TIME_ZONE = 'Australia/Brisbane'
AWS_REGION = 'ap-southeast-2'
BACKUP_KEY = 'Backup'
RETENTION_KEY = 'Retention'

if 'RETENTION_DEFAULT' in os.environ:
    RETENTION_DEFAULT = int(os.environ['RETENTION_DEFAULT'])
if 'TIME_ZONE' in os.environ:
    TIME_ZONE = os.environ['TIME_ZONE']
if 'AWS_REGION' in os.environ:
    AWS_REGION = os.environ['AWS_REGION']
if 'BACKUP_KEY' in os.environ:
    BACKUP_KEY = os.environ['BACKUP_KEY']
if 'RETENTION_KEY' in os.environ:
    RETENTION_KEY = os.environ['RETENTION_KEY']

EC2_CLIENT = boto3.client('ec2', region_name=AWS_REGION)
os.environ['TZ'] = TIME_ZONE


def create_snapshot():
    current_hour = int(datetime.datetime.now().strftime('%H'))

    volumes = EC2_CLIENT.describe_volumes(
        Filters=[
            {'Name': 'tag-key', 'Values': [BACKUP_KEY]},
            {'Name': 'status', 'Values': ['in-use']},
        ]
    ).get(
        'Volumes', []
    )

    print("Number of volumes with backup tag: %d" % len(volumes))

    for volume in volumes:
        vol_id = volume['VolumeId']
        vol_retention = RETENTION_DEFAULT
        snap_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snap_desc = vol_id

        for name in volume['Tags']:
            tag_key = name['Key']
            tag_val = name['Value']

            if tag_key == 'Name':
                snap_desc = vol_id + ' (' + tag_val + ')'

            if tag_key == RETENTION_KEY and tag_val.isdigit():
                vol_retention = int(tag_val)

            if tag_key == BACKUP_KEY:
                backup_mod = False
                if tag_val == '' or tag_val == 'No' or tag_val == 'false':
                    backup_mod = False
                elif tag_val == 'Weekly':
                    backup_mod = 168
                elif tag_val == 'Daily':
                    backup_mod = 24
                elif tag_val == '4/day':
                    backup_mod = 6
                elif tag_val == 'Hourly':
                    backup_mod = 1
                else:
                    print("%s unknown backup schedule %s" % (vol_id, tag_val))
                    continue

        snap_name = 'Backup of ' + snap_desc
        snap_desc = 'Lambda backup ' + snap_date + ' of ' + snap_desc
        delete_ts = '%.0f' % ((vol_retention * 86400) + time.time())

        if backup_mod is False or (current_hour + 10) % backup_mod != 0:
            print("%s is not scheduled this hour" % vol_id)
            continue
        else:
            print("%s is scheduled this hour" % vol_id)

        snap = EC2_CLIENT.create_snapshot(
            VolumeId=vol_id,
            Description=snap_desc,
        )

        print("%s created" % snap['SnapshotId'])

        EC2_CLIENT.create_tags(
            Resources=[snap['SnapshotId']],
            Tags=[
                {'Key': 'Name', 'Value': snap_name},
                {'Key': 'Delete After', 'Value': str(delete_ts)}
            ]
        )


def delete_old_backups(aws_account_ids):
    filters = [
        {'Name': 'tag-key', 'Values': ['Delete After']}
    ]
    snapshot_response = EC2_CLIENT.describe_snapshots(
        OwnerIds=aws_account_ids,
        Filters=filters
    )

    for snap in snapshot_response['Snapshots']:
        for name in snap['Tags']:
            tag_key = name['Key']
            tag_val = name['Value']

            if tag_key == 'Delete After':
                if int(tag_val) < time.time():
                    print("%s is being deleted" % snap['SnapshotId'])
                    EC2_CLIENT.delete_snapshot(SnapshotId=snap['SnapshotId'])
                else:
                    print("%s is safe." % snap['SnapshotId'])


def lambda_handler(event, context):
    aws_account_ids = [context.invoked_function_arn.split(":")[4]]

    create_snapshot()
    delete_old_backups(aws_account_ids)
    return "Successful"
