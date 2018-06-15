# eureka-registrar-decorator
#
# Copyright (c) 2017-Present Pivotal Software, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
import json
import urllib2
import base64
import ssl
import time

urlargs = {}
try:
	ctx = ssl.create_default_context()
	urlargs['context'] = ctx
except:
	ctx = None

def main():
	get_vcap_config()
	if skip_ssl_validation and ctx is not None:
		ctx.check_hostname = False
		ctx.verify_mode = ssl.CERT_NONE
	appinfo = get_application_info()
	service = find_eureka_service(appinfo)
	if service != None:
		start_registrar(service, appinfo)

def detect():
	appinfo = get_application_info()
	service = find_eureka_service(appinfo)
	if service == None:
		sys.exit(1)
	print 'eureka-registrar'

vcap_config = None
log_level = 1
skip_ssl_validation = False

def get_vcap_config():
	global vcap_config
	global log_level
	global skip_ssl_validation
	vcap_config = json.loads(os.getenv('VCAPX_CONFIG', '{}'))
	log_level = vcap_config.get('loglevel', 1)
	skip_ssl_validation = vcap_config.get('skip_ssl_validation', False)

# Get Application Info
#
# Collect the information that will be registered with Eureka
# about this application instance
#
def get_application_info():
	appinfo = {}
	vcap_application = json.loads(os.getenv('VCAP_APPLICATION', '{}'))
	appinfo['name'] = vcap_application.get('application_name')
	if appinfo['name'] == None:
		print >> sys.stderr, "VCAP_APPLICATION must specify application_name"
		sys.exit(1)
	appinfo['instance'] = os.getenv('CF_INSTANCE_INDEX')
	appinfo['hostname'] = vcap_application.get('application_uris')[0]
	appinfo['ipaddress'] = os.getenv('CF_INSTANCE_IP')
	appinfo['port'] = os.getenv('CF_INSTANCE_PORT')
	return appinfo

# Find bound Eureka service
#
def find_eureka_service(appinfo):
	vcap_services = json.loads(os.getenv('VCAP_SERVICES', '{}'))
	for service in vcap_services:
		service_instances = vcap_services[service]
		for instance in service_instances:
			tags = instance.get('tags', []) + instance.get('credentials',{}).get('tags',[])
			if 'spring-cloud' in tags and 'registry' in tags:
				return instance
	return None

def get_access_token(credentials):
	client_id = credentials.get('client_id','')
	client_secret = credentials.get('client_secret','')
	access_token_uri = credentials.get('access_token_uri')
	if access_token_uri is None:
		return None
	req = urllib2.Request(access_token_uri)
	req.add_header('Authorization', 'Basic ' + base64.b64encode(client_id + ":" + client_secret))
	body = "grant_type=client_credentials"
	response = json.load(urllib2.urlopen(req, data=body, **urlargs))
	access_token = response.get('access_token')
	token_type = response.get('token_type')
	return token_type + " " + access_token

def start_registrar(service, appinfo):
	if log_level > 1:
		print "start service-registrar:"
		print json.dumps(service, sys.stderr, indent=4)
		print json.dumps(appinfo, sys.stderr, indent=4)
	credentials = service.get('credentials', {})
	access_token = get_access_token(credentials)
	uri = credentials.get('uri')
	if uri is None:
		print >> sys.stderr, "services of type service-registry must specify a uri"
		return
	base_uri = uri + "/eureka"
	application_uri = base_uri + "/apps/" + appinfo['name']
	instance_uri = application_uri + "/" + appinfo['instance']
	service_info = {
		'access_token': access_token,
		'base_uri': base_uri,
		'application_uri': application_uri,
		'instance_uri': instance_uri,
		'credentials': credentials,
	}
	if log_level > 1:
		list_registered_apps(service_info)
	while True:
		send_heartbeat(service_info, appinfo)
		time.sleep(10)
		service_info['access_token'] = get_access_token(credentials)

def list_registered_apps(service):
	uri = service['base_uri'] + '/apps'
	if log_level > 1:
		print "GET", uri
	req = urllib2.Request(uri)
	req.add_header('Authorization', service['access_token'])
	req.add_header('Accept', 'application/json')
	registrations = json.load(urllib2.urlopen(req, **urlargs))
	print json.dumps(registrations, indent=4)

def send_heartbeat(service, appinfo):
	uri = service['instance_uri']
	if log_level > 1:
		print "PUT", uri
	req = urllib2.Request(uri)
	req.add_header('Authorization', service['access_token'])
	req.add_header('Content-Length', 0)
	req.get_method = lambda : "PUT"
	try:
		urllib2.urlopen(req)
	except urllib2.HTTPError as e:
		if e.code == 404:
			register_service(service, appinfo)
		else:
			raise

def register_service(service, appinfo):
	uri = service['application_uri']
	data = {
		'instance': {
			'instanceId': appinfo['instance'],
			'hostName': appinfo['hostname'],
			'app': appinfo['name'],
			'ipAddr': appinfo['ipaddress'],
			'vipAddress': appinfo['name'],
			'status': 'UP',
			'port': {
				'$': appinfo['port'],
				'@enabled': True,
			},
			'dataCenterInfo': {
				'@class': 'com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo',
				'name': 'MyOwn',
			},
			'homePageUrl': appinfo['hostname'] + '/',
			'statusPageUrl': appinfo['hostname'] + '/info',
			'healthCheckUrl': appinfo['hostname'] + '/health',
		}
	}
	if log_level > 1:
		print "POST", uri
		print json.dumps(data, indent=4)
	req = urllib2.Request(uri)
	req.add_header('Authorization', service['access_token'])
	req.add_header('Content-Type', 'application/json')
	req.get_method = lambda : "POST"
	try:
		urllib2.urlopen(req, data=json.dumps(data), **urlargs)
	except urllib2.HTTPError as e:
		if e.code != 204:
			print >> sys.stderr, json.dumps(data, indent=4)
			print >> sys.stderr, response.status_code
			print >> sys.stderr, response.text
			raise
	if log_level > 1:
		print 'Successfully registered service'

if __name__ == "__main__":
	main()
