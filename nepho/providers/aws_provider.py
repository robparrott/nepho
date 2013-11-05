# coding: utf-8
from os import path

import yaml
import json
import collections
#from nepho.core import common, resource, pattern

import botocore.session
import botocore.hooks
#import botocore.xform_name
from botocore.hooks import first_non_none_response
from botocore.hooks import HierarchicalEmitter

from botocore.compat import copy_kwargs, OrderedDict

import awscli
import awscli.clidriver
import awscli.plugin
#import awscli.argparser
#from awscli import clidriver

#import awscli.clidriver
#from awscli import EnvironmentVariables, __version__
# from awscli.formatter import get_formatter
# from awscli.paramfile import get_paramfile
# from awscli.plugin import load_plugins
# from awscli.argparser import MainArgParser
# from awscli.argparser import ServiceArgParser
# from awscli.argparser import OperationArgParser
# from awscli import clidriver

#import awscli.clidriver

import nepho

        
class AWSProvider(nepho.core.provider.AbstractProvider):   
    """An infrastructure provider class for Vagrant"""

    PROVIDER_ID = "aws"
    TEMPLATE_FILENAME = "cf.json"
    
    def __init__(self, config):
        nepho.core.provider.AbstractProvider.__init__(self,config)    
        
        self.clidriver = self.setup_awscli_driver()
        
    def setup_awscli_driver(self):
        envvars = awscli.EnvironmentVariables
        emitter = botocore.hooks.HierarchicalEmitter()
        session = botocore.session.Session(envvars, emitter)

        session.user_agent_name = 'aws-cli'
        session.user_agent_version = awscli.__version__
        awscli.plugin.load_plugins(session.full_config.get('plugins', {}), event_hooks=emitter)
        return awscli.clidriver.CLIDriver(session=session)

    def validate_template(self, template_str):
        """Validate the template as JSON and CloudFormation."""
        
        try:
            cf_dict = parse_cf_json(template_str)
            template = get_cf_json(cf_dict, pretty=True)
            main_args=[
               'cloudformation',
               'validate-template',
               '--template-body', template
               ]
            self.clidriver.main(main_args)
        except:
            print "Invalid CloudFormation JSON."
            exit(1)
            
    def format_template(self, raw_template):
        """Pretty formats a CF template"""
        cf_dict = parse_cf_json(raw_template)
        return get_cf_json(cf_dict, pretty=True)
        
    def deploy(self):
        """Deploy a given pattern."""
        
        context = self.contextManager.generate()
        raw_template = self.resourceManager.render_template(self.pattern, context)  
        template_json = self.format_template(raw_template) 
              
        stack_name = create_stack_name(context)
        
        main_args=[
               'cloudformation',
               'create-stack',
               '--capabilities', 'CAPABILITY_IAM',
               '--disable-rollback',
               '--stack-name', stack_name
        ]
        
        paramsMap = context['parameters']
        if paramsMap is not None and len(paramsMap.keys()) > 0:
            main_args.append("--parameters")
            for key in paramsMap.keys():
                main_args.append("ParameterKey=%s,ParameterValue=%s" % (key, paramsMap[key]))
        
        main_args.append("--template-body")
        main_args.append( template_json )
        
        self.clidriver.main(main_args)
        
 
    def status(self):
        
        context = self.contextManager.generate()
        stack_name = create_stack_name(context)
        
        main_args=[
               'cloudformation',
               'status',
               '--stack-name', stack_name
               ]
        self.clidriver.main(main_args)
           
    def destroy(self):
        
        
        context = self.contextManager.generate()
        stack_name = create_stack_name(context)
        
        main_args=[
               'cloudformation',
               'delete-stack',
               '--stack-name', stack_name
               ]
        
        try:
            self.clidriver.main(main_args)
        except Exception:
            print "Failed to delete stack"  # TODO move to CLI related code
        print "Successfully deleted stack."
        

def create_stack_name(context):
    return "%s-%s" % (context['cloudlet']['name'], context['blueprint']['name'] )


def parse_cf_json(str):
    cf_dict =  json.loads(str, object_pairs_hook=collections.OrderedDict)
    return cf_dict

def get_cf_json(orderDict, pretty=False):
    outstr = None
    if pretty:
        outstr = json.dumps(orderDict, indent=2, separators=(',', ': '))
    else:
        outstr = json.dumps(orderDict)
    return outstr
    
                