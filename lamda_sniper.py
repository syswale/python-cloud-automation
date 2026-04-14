import boto3
import json
from datetime import datetime, timezone


def lambda_handler(event, context):
    
    print("=" * 55)
    print("EBS Sniper initialized via AWS Lambda...")
    print(f"Execution time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 55)

    
    ec2_client = boto3.client('ec2', region_name='us-east-1')

    # 1. FIND ALL UNATTACHED VOLUMES 
    # 'available' means the volume exists but is not attached to any instance.
    # These are the ones silently billing the company every month.
    response = ec2_client.describe_volumes(
        Filters=[
            {
                'Name': 'status',
                'Values': ['available']
            }
        ]
    )

    volumes = response['Volumes']

    if not volumes:
        print("No unattached volumes found. Account is clean.")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'No unattached volumes found.',
                'deleted': [],
                'failed': []
            })
        }

    print(f"Found {len(volumes)} unattached volume(s). Engaging...\n")

    #  2. LOOP AND DELETE
    # This is the key difference from ebs_sniper.py.
    deleted = []
    failed  = []

    for vol in volumes:
        volume_id = vol['VolumeId']
        size_gb   = vol['Size']
        created   = vol['CreateTime'].strftime('%Y-%m-%d')

        try:
            ec2_client.delete_volume(VolumeId=volume_id)

            # 3. LOG EVERY DELETION TO CLOUDWATCH 
            # print() in Lambda = a CloudWatch log line.
            print(f"  ✓ Target neutralized: {volume_id} | {size_gb} GB | Created: {created} | Est savings: ~${size_gb * 0.08:.2f}/mo")
            deleted.append(volume_id)

        except Exception as e:
            print(f"  ✗ Failed to delete {volume_id}: {str(e)}")
            failed.append({'volume_id': volume_id, 'error': str(e)})

    # FINAL SUMMARY 
    # This block prints a clean debrief to CloudWatch.
    # It also becomes the return value — visible in Lambda test results
    # and passable to downstream services like SNS (email alerts) or Slack.
    total_gb_saved = sum(v['Size'] for v in volumes if v['VolumeId'] in deleted)

    print("\n" + "=" * 55)
    print(f"  Mission complete.")
    print(f"  Deleted : {len(deleted)} volume(s) — {total_gb_saved} GB recovered")
    print(f"  Failed  : {len(failed)} volume(s)")
    print(f"  Monthly savings : ~${total_gb_saved * 0.08:.2f}")
    print("=" * 55)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message'        : 'Sniper execution complete. Volumes terminated.',
            'deleted_count'  : len(deleted),
            'deleted_volumes': deleted,
            'failed_count'   : len(failed),
            'failed_volumes' : failed,
            'gb_recovered'   : total_gb_saved,
            'estimated_monthly_savings': f"${total_gb_saved * 0.08:.2f}"
        })
    }
