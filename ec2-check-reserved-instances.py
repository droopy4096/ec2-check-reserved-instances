#!/usr/bin/python

import sys
import os
import boto
from boto.ec2.connection import EC2Connection
from pprint import pprint

# You can uncomment and set these, or set the env variables AWSAccessKeyId & AWSSecretKey
# AWS_ACCESS_KEY_ID="aaaaaaaaaaaaaaaaaaaa"
# AWS_SECRET_ACCESS_KEY="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

region='us-west-2'

if len(sys.argv) > 1:
    aws_config_file=sys.argv[1]
    import ConfigParser
    cp=ConfigParser.ConfigParser()
    cp.read(aws_config_file)
    aws_defaults=dict(cp.items('default'))
    # print aws_defaults
    AWS_ACCESS_KEY_ID=aws_defaults.get('aws_access_key_id')
    AWS_SECRET_ACCESS_KEY=aws_defaults.get('aws_secret_access_key')
    region=aws_defaults.get('region')


try:
    AWS_ACCESS_KEY_ID
except NameError:
        try:
            AWS_ACCESS_KEY_ID=os.environ['AWSAccessKeyId']
            AWS_SECRET_ACCESS_KEY=os.environ['AWSSecretKey']
        except KeyError:
            print "Please set env variable"
            sys.exit(1)

print 'Processing region: '+region
if region:
        ec2_conn = boto.ec2.connect_to_region(region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
else:
        ec2_conn = EC2Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

reservations = ec2_conn.get_all_instances()
# print reservations


running_instances = {}
for reservation in reservations:
    for instance in reservation.instances:
        print "===> ",instance.id, instance.instance_type, instance.state, instance.placement
        if instance.state != "running":
            sys.stderr.write("Disqualifying instance %s: not running\n" % ( instance.id ) )
        elif instance.spot_instance_request_id:
                sys.stderr.write("Disqualifying instance %s: spot\n" % ( instance.id ) )
        else:
            az = instance.placement
            instance_type = instance.instance_type
            running_instances[ (instance_type, az ) ] = running_instances.get( (instance_type, az ) , 0 ) + 1


###REFACTORED running_instances = {}
###REFACTORED for reservation in reservations:
###REFACTORED         for instance in reservation.instances:
###REFACTORED                 if instance.state != "running":
###REFACTORED                         sys.stderr.write("Disqualifying instance %s: not running\n" % ( instance.id ) )
###REFACTORED                 elif instance.spot_instance_request_id:
###REFACTORED                         sys.stderr.write("Disqualifying instance %s: spot\n" % ( instance.id ) )
###REFACTORED                 else:
###REFACTORED                         if instance.vpc_id:
###REFACTORED                                 print "Does not support vpc yet, please be careful when trusting these results"
###REFACTORED                         else:
###REFACTORED                                 az = instance.placement
###REFACTORED                                 instance_type = instance.instance_type
###REFACTORED                                 running_instances[ (instance_type, az ) ] = running_instances.get( (instance_type, az ) , 0 ) + 1
###REFACTORED 

# pprint( running_instances )


reserved_instances = {}
for reserved_instance in ec2_conn.get_all_reserved_instances():
    if reserved_instance.state != "active":
        sys.stderr.write( "Excluding reserved instances %s: no longer active\n" % ( reserved_instance.id ) )
    else:
        az = reserved_instance.availability_zone
        instance_type = reserved_instance.instance_type
        reserved_instances[( instance_type, az) ] = reserved_instances.get ( (instance_type, az ), 0 )  + reserved_instance.instance_count

# pprint( reserved_instances )


# this dict will have a positive number if there are unused reservations
# and negative number if an instance is on demand
instance_diff = dict([(x, reserved_instances[x] - running_instances.get(x, 0 )) for x in reserved_instances.keys()])

# instance_diff only has the keys that were present in reserved_instances. There's probably a cooler way to add a filtered dict here
for placement_key in running_instances:
    if not placement_key in reserved_instances:
        instance_diff[placement_key] = -running_instances[placement_key]

## pprint ( instance_diff )

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
