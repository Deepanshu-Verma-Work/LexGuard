import boto3
import time

ec2 = boto3.resource('ec2', region_name='us-east-1')
client = boto3.client('ec2', region_name='us-east-1')

def cleanup_vpc(vpc_id):
    print(f"Cleaning up VPC: {vpc_id}")
    vpc = ec2.Vpc(vpc_id)
    
    # 1. Delete Internet Gateways
    for igw in vpc.internet_gateways.all():
        print(f"  Detaching IGW {igw.id}")
        vpc.detach_internet_gateway(InternetGatewayId=igw.id)
        print(f"  Deleting IGW {igw.id}")
        igw.delete()

    # 2. Delete Subnets
    for subnet in vpc.subnets.all():
        print(f"  Deleting Subnet {subnet.id}")
        # Terminate any lingering instances? (Should be done, but check)
        # Assuming safe.
        try:
            subnet.delete()
        except Exception as e:
            print(f"    Error: {e}")

    # 3. Delete Route Tables
    for rt in vpc.route_tables.all():
        if not rt.associations: # Main table has associations usually? No, explicit ones.
             # Check if main
            is_main = False
            for assoc in rt.associations:
                if assoc.main:
                    is_main = True
                    break
            if not is_main:
                print(f"  Deleting RT {rt.id}")
                try:
                    rt.delete()
                except Exception as e:
                    print(f"    Error: {e}")

    # 4. Delete Security Groups
    # SGs can reference each other. Loop until deleted or stuck.
    sgs = list(vpc.security_groups.all())
    print(f"  Found {len(sgs)} SGs")
    
    # Attempt to delete all non-default
    for _ in range(3):
        for sg in sgs:
            if sg.group_name == 'default':
                continue
            try:
                print(f"    Deleting SG {sg.id}")
                sg.delete()
            except Exception as e:
                pass # references?
    
    # 5. Delete VPC
    print(f"  Deleting VPC {vpc.id}")
    try:
        vpc.delete()
        print("  SUCCESS")
    except Exception as e:
        print(f"  FAILED to delete VPC: {e}")


# Find CaseChat VPCs
vpcs = client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['CaseChat-VPC']}])
if not vpcs['Vpcs']:
    print("No CaseChat VPCs found.")
else:
    for v in vpcs['Vpcs']:
        cleanup_vpc(v['VpcId'])

print("--- VPC CLEANUP DONE ---")
