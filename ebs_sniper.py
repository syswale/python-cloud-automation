import boto3
from datetime import datetime


def get_unattached_volumes(ec2_client):
    """Scans AWS and return a list of unattached EBS volumes."""

    response = ec2_client.describe_volumes(
        Filters=[
            {
                'Name': 'status',
                'Values': ['available']
            }
        ]
    )
    return response['Volumes']


def print_dashboard(volumes):
    """Print a clean recon report of all orphaned volumes."""

    print("\n" + "=" * 55)
    print("        EBS SNIPER — PHASE 2: DESTROY")
    print("=" * 55)

    total_gb = 0

    for vol in volumes:
        volume_id   = vol['VolumeId']
        size_gb     = vol['Size']
        volume_type = vol['VolumeType']
        created     = vol['CreateTime'].strftime('%Y-%m-%d')

        name = "untagged"
        for tag in vol.get('Tags', []):
            if tag['Key'] == 'Name':
                name = tag['Value']

        total_gb += size_gb

        print(f"\n  Volume ID  : {volume_id}")
        print(f"  Name       : {name}")
        print(f"  Size       : {size_gb} GB ({volume_type})")
        print(f"  Created    : {created}")
        print(f"  Est. cost  : ~${size_gb * 0.08:.2f}/month")
        print("  " + "-" * 45)

    print(f"\n  Total wasted storage : {total_gb} GB")
    print(f"  Total monthly waste  : ~${total_gb * 0.08:.2f}/month\n")
    print("=" * 55)


def delete_volumes(ec2_client, volumes):
    """
    Ask for confirmation, then delete every volume in the list.
    """

   
    confirm = input("\n  ⚠  Do you want to delete these volumes? (y/n): ").strip().lower()

    if confirm != 'y':
        # Anything that isn't a clean "y" aborts — n, no, enter, typo, all safe
        print("\n  Sniper standing down. No volumes were deleted.\n")
        return

    print("\n  Target lock confirmed. Engaging...\n")

    deleted_count = 0
    failed_count  = 0

    for vol in volumes:
        volume_id = vol['VolumeId']

        try:
            ec2_client.delete_volume(VolumeId=volume_id)

            print(f"  ✓ Target neutralized: {volume_id} deleted.")
            deleted_count += 1

        except Exception as e:
            # Catches edge cases: volume got attached between scan and delete,
            # or an IAM permission error, or an API hiccup.
            print(f"  ✗ Failed to delete {volume_id}: {e}")
            failed_count += 1

    # Final
    print("\n" + "=" * 55)
    print(f"  Mission complete.")
    print(f"  Deleted : {deleted_count} volume(s)")
    if failed_count > 0:
        print(f"  Failed  : {failed_count} volume(s) — check errors above")
    print("=" * 55 + "\n")


def run():
    """Main entry point. Wires everything together."""

    # Create the client once and pass it around — clean and efficient
    ec2_client = boto3.client('ec2', region_name='us-east-1')

    print("\n  [*] Scanning us-east-1 for orphaned EBS volumes...")
    volumes = get_unattached_volumes(ec2_client)

    if not volumes:
        print("\n  ✓ No unattached volumes found. Account is clean.\n")
        return

    print(f"  [!] Found {len(volumes)} unattached volume(s).")

    # 1: show what we found
    print_dashboard(volumes)

    # 2: offer to destroy them
    delete_volumes(ec2_client, volumes)


if __name__ == '__main__':
    run()
