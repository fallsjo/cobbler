# friendly OO python API module for BootConf 
#
# Michael DeHaan <mdehaan@redhat.com>

import os
import traceback

import config
import util
import sync

class BootAPI:

    """
    Constructor...
    """
    def __init__(self):
       self.last_error = ''
       self.config = config.BootConfig(self)
       self.utils  = util.BootUtil(self,self.config)
       # if the file already exists, load real data now
       try:
           if os.path.exists(self.config.config_file):
              self.config.deserialize()
       except:
           # traceback.print_exc()
           util.warning("Could not parse config file, recreating")
           try:
               self.config.serialize()
           except:
               # traceback.print_exc()
               pass
       if not os.path.exists(self.config.config_file):
           self.config.serialize()


    def show_error(self):
       print self.last_error

    """
    Forget about current list of groups, distros, and systems
    """
    def clear(self):
       self.config.clear()

    """
    Return the current list of systems
    """
    def get_systems(self):
       return self.config.get_systems()

    """
    Return the current list of groups
    """
    def get_groups(self):
       return self.config.get_groups()

    """
    Return the current list of distributions
    """
    def get_distros(self):
       return self.config.get_distros()

    """
    Create a blank, unconfigured system
    """
    def new_system(self):
       return System(self,None)

    """
    Create a blank, unconfigured distro
    """
    def new_distro(self):
       return Distro(self,None)

    """
    Create a blank, unconfigured group
    """
    def new_group(self):
       return Group(self,None)

    """
    See if all preqs for network booting are operational
    """
    def check(self):
       return self.utils.check_install()

    """
    Update the system with what is specified in the config file
    """ 
    def sync(self,dry_run=True):
       self.config.deserialize();
       configurator = sync.BootSync(self)
       configurator.sync(dry_run)

    """
    Save the config file
    """
    def serialize(self):
       self.config.serialize() 
    
    """
    Make the API's internal state reflect that of the config file
    """
    def deserialize(self):
       self.config.deserialize()

#--------------------------------------

"""
Base class for any serializable lists of things...
"""
class Collection:

    """
    Return anything named 'name' in the collection, else return None
    """
    def find(self,name):
        if name in self.listing.keys():
            return self.listing[name]
        return None

    """
    Return datastructure representation (to feed to serializer)
    """
    def to_ds(self):
        return [x.to_ds() for x in self.listing.values()]
    
     
    """
    Add an object to the collection, if it's valid
    """
    def add(self,ref):
        if ref is None or not ref.is_valid(): 
            self.last_error = "Referenced parameter is not valid"
            return False
        self.listing[ref.name] = ref
        # removed auto serialization ... now the API must call it explicitly.
        return True

    """
    Printable representation
    """
    def __str__(self):
        buf = ""
        values = sorted(self.listing.values())
        if len(values) > 0: 
           for v in values: buf = buf + str(v) + "\n"
           return buf
        else:
           return "(Empty)"

    def contents(self):
        return self.listing.values()

#--------------------------------------------

"""
A distro represents a network bootable matched set of kernels
and initrd files
"""
class Distros(Collection):

    def __init__(self,api,seed_data):
        self.api = api
        self.listing = {}
        if seed_data is not None:
           for x in seed_data: 
               self.add(Distro(self.api,x))
    """
    Remove element named 'name' from the collection
    """
    def remove(self,name):
        # first see if any Groups use this distro
        for k,v in self.api.config.groups.listing.items():
            if v.distro == name:
               self.last_error = "Cannot delete, this distro is referenced by a group"
               return False
        if name in self.listing:
            del self.listing[name]
            return True
        self.last_error = "Cannot delete a distro that does not exist"
        return False
    

#--------------------------------------------

"""
A group represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' group.
"""
class Groups(Collection):

    def __init__(self,api,seed_data):
        self.api = api
        self.listing = {}
        if seed_data is not None:
           for x in seed_data: 
               self.add(Group(self.api,x))
    """
    Remove element named 'name' from the collection
    """
    def remove(self,name):
        for k,v in self.api.config.systems.listing.items():
           if v.group == name:
               self.last_error = "Cannot delete, this group is referenced by a system"
               return False
        if name in self.listing:
            del self.listing[name]
            return True
        self.last_error = "Cannot delete a group that does not exist"
        return False
    

#--------------------------------------------

"""
Systems are hostnames/MACs/IP names and the associated groups
they belong to.
"""
class Systems(Collection):

    def __init__(self,api,seed_data):
        self.api = api
        self.listing = {}
        if seed_data is not None:
           for x in seed_data: 
               self.add(System(self.api,x))
    """
    Remove element named 'name' from the collection
    """
    def remove(self,name):
        if name in self.listing:
            del self.listing[name]
            return True
        self.last_error = "Cannot delete a system that does not exist"
        return False
    

#-----------------------------------------

"""
An Item is a serializable thing that can appear in a Collection
"""
class Item:
  
    def set_name(self,name):
        self.name = name
        return True

    def to_ds(self):
        raise "not implemented"
   
    def is_valid(self):
        return False 

#------------------------------------------

class Distro(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.kernel = None
        self.initrd = None
        if seed_data is not None:
           self.name = seed_data['name']
           self.kernel = seed_data['kernel']
           self.initrd = seed_data['initrd']

    def set_kernel(self,kernel):
        if self.api.utils.find_kernel(kernel):
            self.kernel = kernel
            return True
        return False

    def set_initrd(self,initrd):
        if self.api.utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        return False

    def is_valid(self):
        for x in (self.name,self.kernel,self.initrd):
            if x is None: return False
        return True

    def to_ds(self):
        return { 
           'name': self.name, 
           'kernel': self.kernel, 
           'initrd' : self.initrd
        }

    def __str__(self):
        return "%s : kernel=%s | initrd=%s |" % (self.name,self.kernel,self.initrd)

#---------------------------------------------

class Group(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.distro = None # a name, not a reference
        self.kickstart = None
        if seed_data is not None:
           self.name        = seed_data['name']
           self.distro    = seed_data['distro']
           self.kickstart = seed_data['kickstart'] 

    def set_distro(self,distro_name):
        if self.api.get_distros().find(distro_name):
            self.distro = distro_name
            return True
        self.last_error = "Specified distro doesn't exist"
        return False

    def set_kickstart(self,kickstart):
        if self.api.utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        self.last_error = "Specified kickstart doesn't exist"
        return False

    def is_valid(self):
        for x in (self.name, self.distro, self.kickstart):
            if x is None: return False
        return True

    def to_ds(self):
        return { 
            'name' : self.name,
            'distro' : self.distro,
            'kickstart' : self.kickstart
        }

    def __str__(self):
        return "%s : distro=%s | kickstart=%s" % (self.name, self.distro, self.kickstart)

#---------------------------------------------

class System(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.group = None # a name, not a reference
        if seed_data is not None:
           self.name = seed_data['name']
           self.group = seed_data['group']
    
    """
    A name can be a resolvable hostname (it instantly resolved and replaced with the IP), 
    any legal ipv4 address, or any legal mac address. ipv6 is not supported yet but _should_ be.
    See utils.py
    """
    def set_name(self,name):
        new_name = self.api.utils.find_system_identifier(name) 
        if new_name is None or new_name == False:
            return False
        self.name = name  # we check it add time, but store the original value.
        return True

    def set_group(self,group_name):
        if self.api.get_groups().find(group_name):
            self.group = group_name
            return True
        return False

    def is_valid(self):
        for x in (self.name, self.group):
            if x is None: return False
        return True

    def to_ds(self):
        return {
           'name'   : self.name,
           'group'  : self.group 
        }

    def __str__(self):
        return "%s : group=%s" % (self.name,self.group)


