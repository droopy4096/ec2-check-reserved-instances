#!/usr/bin/python

import ConfigParser
import argparse
import sys
import os
import boto
from boto.ec2.connection import EC2Connection
from pprint import pprint

# You can uncomment and set these, or set the env variables AWSAccessKeyId & AWSSecretKey
# AWS_ACCESS_KEY_ID="aaaaaaaaaaaaaaaaaaaa"
# AWS_SECRET_ACCESS_KEY="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
# AWS_REGION="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

class AWSLister(object):
    def __init__(self,access_key, secret_key, region):
        self.ec2_conn = boto.ec2.connect_to_region(region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key)
        self.instances=[]
        self.reserved_instances=[]

    def get_running_instances(self):
        reservations = self.ec2_conn.get_all_instances()
        self.instances=[]

        running_instances = {}
        for reservation in reservations:
            self.instances=self.instances+reservation.instances
            for instance in reservation.instances:
                # print "===> ",instance.id, instance.instance_type, instance.state, instance.placement
                if instance.state != "running":
                    # sys.stderr.write("Disqualifying instance %s: not running\n" % ( instance.id ) )
                    pass
                elif instance.spot_instance_request_id:
                    # sys.stderr.write("Disqualifying instance %s: spot\n" % ( instance.id ) )
                    pass
                else:
                    az = instance.placement
                    instance_type = instance.instance_type
                    running_instances[ (instance_type, az ) ] = running_instances.get( (instance_type, az ) , 0 ) + 1

        return running_instances

    def get_reserved_instances(self):
        self.reserved_instances=self.ec2_conn.get_all_reserved_instances()
        reserved_instances = {}
        for reserved_instance in self.reserved_instances:
            if reserved_instance.state == "active":
                az = reserved_instance.availability_zone
                instance_type = reserved_instance.instance_type
                reserved_instances[( instance_type, az) ] = reserved_instances.get ( (instance_type, az ), 0 )  + reserved_instance.instance_count

        return reserved_instances

    def get_instance_diff(self,reserved_instances=None,running_instances=None):
        if reserved_instances is None:
            reserved_instances=self.get_reserved_instances()
        if running_instances is None:
            running_instances=self.get_running_instances()
        instance_diff = dict([(x, reserved_instances[x] - running_instances.get(x, 0 )) for x in reserved_instances.keys()])
        for placement_key in running_instances:
            if not placement_key in reserved_instances:
                instance_diff[placement_key] = -running_instances[placement_key]
        return instance_diff

def main():
    region='us-west-2'

    parser = argparse.ArgumentParser()
    parser.add_argument('--aws_config', help='AWS Config file');
    parser.add_argument('--access_key', help='Access Key');
    parser.add_argument('--secret_key', help='Secret Key');
    parser.add_argument('--region', help='Region');
    args = parser.parse_args()
    if args.aws_config:
        print "> Using config: ",args.aws_config
        cp=ConfigParser.ConfigParser()
        cp.read(os.path.expanduser(args.aws_config))
        aws_defaults=dict(cp.items('default'))
        AWS_ACCESS_KEY_ID=aws_defaults.get('aws_access_key_id')
        AWS_SECRET_ACCESS_KEY=aws_defaults.get('aws_secret_access_key')
        AWS_REGION=aws_defaults.get('region')
    else:
        AWS_ACCESS_KEY_ID = args.access_key
        AWS_SECRET_ACCESS_KEY = args.secret_key
        AWS_REGION = args.region
    
    print '> Processing region: '+AWS_REGION


    aws_lister=AWSLister(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY,AWS_REGION)
    running_instances=aws_lister.get_running_instances()
    reserved_instances=aws_lister.get_reserved_instances()
    instance_diff=aws_lister.get_instance_diff(reserved_instances,running_instances)

    ## List instances:
    print "\n> Instances:"
    for instance in aws_lister.instances:
        print "===> ",instance.id, instance.instance_type, instance.placement, instance.state
        if instance.state != "running":
            sys.stderr.write("Disqualifying instance %s: not running\n" % ( instance.id ) )
        elif instance.spot_instance_request_id:
            sys.stderr.write("Disqualifying instance %s: spot\n" % ( instance.id ) )

    ## List reservations
    print "\n> Reservations:"
    for reserved_instance in aws_lister.reserved_instances:
        if reserved_instance.state != "active":
            sys.stderr.write( "Excluding reserved instances %s: no longer active\n" % ( reserved_instance.id ) )
        else:
            print "---> ", reserved_instance.id, reserved_instance.instance_type, reserved_instance.availability_zone

    print ""

    unused_reservations = dict((key,value) for key, value in instance_diff.iteritems() if value > 0)
    if unused_reservations == {}:
        print "Congratulations, you have no unused reservations"
    else:
        for unused_reservation in unused_reservations:
            print "UNUSED RESERVATION!\t(%s)\t%s\t%s" % ( unused_reservations[ unused_reservation ], unused_reservation[0], unused_reservation[1] )

    print ""

    unreserved_instances = dict((key,-value) for key, value in instance_diff.iteritems() if value < 0)
    if unreserved_instances == {}:
        print "Congratulations, you have no unreserved instances"
    else:
        for unreserved_instance in unreserved_instances:
            print "Instance not reserved:\t(%s)\t%s\t%s" % ( unreserved_instances[ unreserved_instance ], unreserved_instance[0], unreserved_instance[1] )

    # print running_instances
    if running_instances:
        qty_running_instances = reduce( lambda x, y: x+y, running_instances.values() )
    else:
        qty_running_instances = 0
    qty_reserved_instances = reduce( lambda x, y: x+y, reserved_instances.values() )

    print "\n(%s) running instances\n(%s) reservations" % ( qty_running_instances, qty_reserved_instances )

if __name__ == '__main__':
    main()
