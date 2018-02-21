# Lambda EBS Snapshot Manager for Python 3.6
---
This is a fork of https://github.com/doximity/lambda-ebs-snapshots
Modified fork of: https://github.com/Brayyy/Lambda-EBS-Snapshot-Manager

Create a Lambda script to schedule creation and clearing of EBS snapshots.

- To tag an EBS volume for backup, add a tag key: "Backup" with a value: how often to snapshot.
Values for "Backup" key: Hourly, 4/day, Daily, Weekly, No

- Optionally, add the key "Retention" with the number of days to override the default amount in the function.
Values for "Retention" key: (days)

- Snapshots will be created with a tag key: "Delete After", value: seconds to exists after creation. After this period, they're purged. If no key is set, they're purged after the default retention period you set.

- Snapshots will be named "Backup of vol-1234asdf1234asdf (Volume Name)".

Notes:
 - 4/day snapshots will run 0000, 0600, 1200, 1800 in UTC time. If you need to change this, add the time difference to current_hour, ie +10 hours for Brisbane = 
 if backup_mod is False or (current_hour + 10) % backup_mod != 0:

- This script will only snapshot volumes which are 'in-use'. If a volume is detached or in another state, it won't. You can change this by deleting the line {'Name': 'status', 'Values': ['in-use']},

- If you stop an instance, this script will still snapshot the attached volumes if they're tagged. If previous snapshots have been taken of the volume, you won't be billed for additional storage since snapshots are incremental, it will just clog up your snapshots in AWS.

 - If you know a way to modify this to only snapshot volumes attacheed to running instances, please let me know/send a pull request.

How to:
1. Create a new role with the IAM policy below.
2. Create Lambda function with below settings
3. Add code to Lambda
4. Checkout CloudWatch logs to confirm nil errors

![EBS Volume tagging example](/example-tagged-volume.png)

Lambda config:
- Runtime: Python 3.6
- Handler: lambda_function.lambda_handler or filename.lambda_handler
- Role: [role as specified below]
- Memory: 128
- Timeout: 5 sec
- No VPC
- Add an hourly trigger using "CloudWatch Events - Schedule" / cron(0 * ? * * *) 

IAM Lambda Role:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:*"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVolumes",
                "ec2:DescribeSnapshots",
                "ec2:CreateSnapshot",
                "ec2:DeleteSnapshot",
                "ec2:CreateTags",
                "ec2:ModifySnapshotAttribute",
                "ec2:ResetSnapshotAttribute"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

