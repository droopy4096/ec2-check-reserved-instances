# https://cloudpages.wordpress.com/2013/12/18/listing-all-of-your-ec2-instances-using-boto/
import argparse
import boto.ec2
import ConfigParser
 
access_key = ''
secret_key = ''
 
def get_ec2_instances(region):
    ec2_conn = boto.ec2.connect_to_region(region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key)
    reservations = ec2_conn.get_all_reservations()
    for reservation in reservations:    
        print region+':',reservation.instances
 
    for vol in ec2_conn.get_all_volumes():
        print region+':',vol.id
 
    
 
def main():
    regions = ['us-east-1','us-west-1','us-west-2','eu-west-1','sa-east-1',
                'ap-southeast-1','ap-southeast-2','ap-northeast-1']
    parser = argparse.ArgumentParser()
    parser.add_argument('--aws_config', help='AWS Config file');
    parser.add_argument('--access_key', help='Access Key');
    parser.add_argument('--secret_key', help='Secret Key');
    args = parser.parse_args()
    global access_key
    global secret_key
    if args.aws_config:
	cp=ConfigParser.ConfigParser()
	cp.read(args.aws_config)
	aws_defaults=cp.defaults()
	access_key=aws_defaults.get('aws_access_key_id')
	secret_key=aws_defaults.get('aws_secret_access_key')
    else:
    	access_key = args.access_key
    	secret_key = args.secret_key
    
    for region in regions: get_ec2_instances(region)
 
if  __name__ =='__main__':main()
