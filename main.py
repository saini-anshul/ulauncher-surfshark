import os
import os.path
import json
import re
import pathlib
import time
import subprocess as sp
from gi.repository import Notify
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    ItemEnterEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
)
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


class Utils:
    # Returns absolute path
    @staticmethod
    def get_path(filename):
        current_dir = pathlib.Path(__file__).parent.absolute()
        return f"{current_dir}/{filename}"
    
    # Show GUI notification
    @staticmethod
    def notify(title, message):
        Notify.init("SurfsharkVPNExt")
        notification = Notify.Notification.new(
            title,
            message,
            Utils.get_path("images/icon.svg"),
        )
        notification.set_timeout(1000)
        notification.show()
    
    # Returns list of available server connection types and corresponding action keyword
    @staticmethod
    def get_available_connection_types():
        available_conn_types = [
            {
                "name": "UDP",
                "description": "Connect to VPN using UDP",
                "action": "udp"
            },
            {
                "name": "TCP",
                "description": "Connect to VPN using TCP",
                "action": "tcp"
            },
            {
                "name": "Static UDP",
                "description": "Connect to VPN with Static IP - UDP",
                "action": "st_udp"
            },
            {
                "name": "Static TCP",
                "description": "Connect to VPN with Static IP - TCP",
                "action": "st_tcp"
            },
            {
                "name": "Multipoint UDP",
                "description": "Connect to VPN with Multipoint UDP",
                "action": "mp_udp"
            },
            {
                "name": "Multipoint TCP",
                "description": "Connect to VPN with Multipoint TCP",
                "action": "mp_tcp"
            }
        ]
        return available_conn_types


class Surf:
    openvpn_bin_paths = ["/usr/bin/openvpn", "/bin/openvpn", "/usr/sbin/openvpn"]
    # Some additional multihop server profiles that do not follow naming trend
    special_server_profiles = [
        "sg-in.prod.surfshark.com_tcp.ovpn",
        "sg-in.prod.surfshark.com_udp.ovpn",
        "45.83.91.133_tcp.ovpn",
        "45.83.91.133_udp.ovpn"
    ]
    country_mapping = []
    all_servers = [] # store profile name for all available servers
    reg_servers = [] # stores details of all regular VPN servers
    st_servers = [] # stores details of all static ip server profiles
    mp_servers = [] # stores details of all multi-point/multi-hop servers
    
    # Returns the openvpn bin path
    def get_installed_path(self):
        for path in self.openvpn_bin_paths:
            if os.path.exists(path):
                return path
        return False

    # Checks if openvpn is installed
    def is_installed(self):
        return bool(self.installed_path)

    # Returns server details based on the ovpn file name and server-country mapping file
    def get_server_details(self, profile_name):
        if not profile_name:
            return None
        
        server_code = None
        detail_object = None
        if len(profile_name.split(".prod.surfshark.com")) > 1:
            server_code = profile_name.split(".prod.surfshark.com")[0]
            # check for mp server profiles
            if 'mp0' in server_code:
                server_code = server_code.split("-mp0")[0]
            # check for st server profiles
            if 'st0' in server_code:
                server_code = server_code.split("-st0")[0]
        elif profile_name[:1].isdigit():
            # Some servers configs are named as IP addresses
            server_code = profile_name.split("_")[0]
        
        if server_code:
            try:
                detail_object = next(d for d in self.country_mapping if d["code"] == server_code)
            except StopIteration:
                None # Server mapping not found

        if not detail_object:
            return {
                "code": server_code if server_code else profile_name,
                "country": server_code if server_code else profile_name,
                "city": "",
                "altSearch": " "
            }
            
        return detail_object

    # Returns flag file name based on country name
    def flag_name(self, country_name):
        return ((country_name.lower().replace(" ", "-") + "-flag.svg") if country_name else "")

    # Returns the server count if server is mp or st-ip, None otherwise
    def get_speacial_server_number(self, profile_name):
        if not profile_name or ('mp0' not in profile_name and 'st0' not in profile_name):
            return ""
        
        try:
            return (" " + re.search('[m|s][p|t](.*)\.prod', profile_name).group(1))
        except AttributeError:
            return ""

    # Populate server objects utilizing details object
    def populate_server_object(self, server_details, profile_name):
        if not server_details or not profile_name:
            return None
        
        return {
            "country": server_details["country"],
            "city": server_details["city"] + self.get_speacial_server_number(profile_name),
            "alt_word": server_details["altSearch"],
            "flag_file": self.flag_name(server_details["country"]),
            "conn_type": self.get_conn_type_from_profile_name(profile_name),
            "server_profile": profile_name
        }

    # Populate list of server objects with details
    def populate_server_object_list(self, profile_list):
        server_list = []

        if profile_list:
            for profile in profile_list:
                server_list.append(self.populate_server_object(self.get_server_details(profile), profile))

        return server_list
    
    # Reload ovpn server profile details to memory 
    def refresh_server_list(self):
        self.all_servers = [f for f in os.listdir(self.surfshark_dir_path) if os.path.isfile(os.path.join(self.surfshark_dir_path, f))]
        
        # load regular servers list
        temp_list = list(
            filter(
                lambda s: 'st0' not in s and 'mp0' not in s, self.all_servers
            )
        )
        # Remove special mp server profiles
        for sp_server in self.special_server_profiles:
            if sp_server in temp_list:
                temp_list.remove(sp_server)

        self.reg_servers = self.populate_server_object_list(temp_list)
        temp_list.clear()

        # load static ip servers list
        temp_list = list(
            filter(
                lambda s: 'st0' in s, self.all_servers
            )
        )

        self.st_servers = self.populate_server_object_list(temp_list)
        temp_list.clear()

        # load multipoint servers list
        temp_list = list(
            filter(
                lambda s: 'mp0' in s, self.all_servers
            )
        )
        # Add special mp server profiles
        temp_list.extend(self.special_server_profiles)
        self.mp_servers = self.populate_server_object_list(temp_list)
    
    # Connect to server using ovpn profile
    def connect(self, server):
        if not self.is_installed():
            return
        server_details = self.get_server_details(server)
        Utils.notify(
            f'Connecting to {server_details["country"]} - {server_details["city"]}...',
            "Connecting you to Surfshark.",
        )
        # Need to run command in new bash and background to avoid locking extension
        #os.system(f"bash -lc \"pkexec {self.installed_path} --config {self.surfshark_dir_path}/{server} --auth-user-pass {self.config_file_path}\" </dev/null &>/dev/null &")
        sp.call(["pkexec", "bash", "-lc", f"{self.installed_path} --config {self.surfshark_dir_path}/{server} --auth-user-pass {self.config_file_path} &"])
        time.sleep(2)
        if (self.get_status()):
            Utils.notify(
                f'Connected to {server_details["country"]} - {server_details["city"]}.',
                "Connected to Surfshark VPN.",
            )
        else:
            Utils.notify(
                f'Error connecting to {server_details["country"]} - {server_details["city"]}.',
                "There was an error connecting to Surfshark VPN.",
            )

    # Disconnects openvpn connection, if any 
    def disconnect(self):
        if not self.is_installed():
            return
        Utils.notify(
            "Disconnecting...",
            "Disconnecting you from Surfshark.",
        )
        #os.system(f"pgrep -f {self.installed_path}\ --config | pkexec xargs kill ")
        ovpn_process_id = sp.Popen(["pgrep", "-f", f"{self.installed_path} --config"], stdout=sp.PIPE)
        sp.call(["pkexec", "xargs", "kill"], stdin=ovpn_process_id.stdout)
        time.sleep(2)
        if not self.get_status():
            Utils.notify(
                "Disconnected.",
                "Disconnected from Surfshark VPN.",
            )
        else:
            Utils.notify(
                "Error while disconnecting.",
                "There was an error while disconnecting from Surfshark VPN.",
            )

    # extracts connection type from profile name and returns in user-friendly text
    def get_conn_type_from_profile_name(self, profile_name):
        if not profile_name:
            return None
        
        if 'mp0' in profile_name or profile_name in self.special_server_profiles:
            if 'tcp.ovpn' in profile_name:
                return "Multi-Point TCP"
            else:
                return "Multi-Point UDP"
        elif 'st0' in profile_name:
            if 'tcp.ovpn' in profile_name:
                return "Static-IP TCP"
            else:
                return "Static-IP UDP"
        elif 'tcp.ovpn' in profile_name:
            return "TCP"
        else:
            return "UDP"
    
    # Provides the status of VPN connection - returns server details object if connected
    def get_status(self):
        connected_server_profile = sp.getoutput(f"pgrep -af {self.installed_path}\ --config | awk '{{print $4}}' | awk -F/ '{{print $NF}}' ")
        if (connected_server_profile):
            return self.populate_server_object(self.get_server_details(connected_server_profile), connected_server_profile)
        
        return None
    
    # Removes all ovpn profiles from server_profile folder and re-download them from Surfshark
    def refresh_openvpn_connections(self):
        Utils.notify(
            "Refreshing...",
            "Refreshing Surfshark VPN connection profiles.",
        )
        os.system(f"rm {self.surfshark_dir_path}/*.ovpn {self.surfshark_dir_path}/configurations ")
        os.system(f"wget https://my.surfshark.com/vpn/api/v1/server/configurations -P {self.surfshark_dir_path} ")
        os.system(f"unzip {self.surfshark_dir_path}/configurations -d {self.surfshark_dir_path} ")
        os.system(f"rm {self.surfshark_dir_path}/configurations ")
        self.refresh_server_list()
        
        Utils.notify(
            "Refreshed.",
            "Surfshark VPN connection profiles refreshed.",
        )
    
    # Create and modify credentials file
    def update_credential_file(self, uname, passwd):
        if not os.path.exists(self.config_file_path):
            os.system(f"echo \"\n\" > {self.config_file_path} && chmod 600 {self.config_file_path} ") # need to create two line to open stream for sed to update passowrd at line 2
        if uname:
            os.system(f"sed -i \"1s/.*/{uname}/\" {self.config_file_path} ")
        if passwd:
            os.system(f"sed -i \"2s/.*/{passwd}/\" {self.config_file_path} ")

    def __init__(self):
        self.installed_path = self.get_installed_path()
        self.country_mapping = json.load(open(Utils.get_path("server_country_map.json"), "r"))
        self.surfshark_dir_path = Utils.get_path("server_profiles")
        self.config_file_path = Utils.get_path("service_credentials.conf")
        # In case user deletes the folder with ovpn profiles manually
        if not os.path.exists(self.surfshark_dir_path):
            os.system(f"mkdir {self.surfshark_dir_path} ")
         
        self.refresh_server_list()


class SurfExtension(Extension):
    keyword = None
    max_server_entries = None

    def __init__(self):
        super(SurfExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.surf = Surf()
    
    # Update service credentials
    def update_username(self, uname):
        self.surf.update_credential_file(uname, None)
        
    def update_password(self, passwd):
        self.surf.update_credential_file(None, passwd)
    # End update service credentials
    
    # Filters the provided server list based on search query and server type 
    def filter_server_list(self, query, server_type, server_list):
        query = query.lower() if query else ""
        if query:
            return [s for s in server_list if ((s["country"].lower().startswith(query) 
                                                    or s["alt_word"].lower().startswith(query) 
                                                    or s["city"].lower().startswith(query))
                                     and server_type in s["conn_type"].lower())]
        else:
            return [s for s in server_list if server_type in s["conn_type"].lower()]
    
    # Returns servers based on server query and connection type selected
    def get_server_result_items(self, query, server_type):
        #server_type = (server_type.lower() + ".ovpn") if server_type else "udp.ovpn"
        server_type = server_type.lower() if server_type else "udp"
        items = []
        data = []
        
        # multihop connections
        if server_type.startswith('mp'):
            server_type = server_type.replace('mp_', '')
            data = self.filter_server_list(query, server_type, self.surf.mp_servers)
            
        # static ip connections
        elif server_type.startswith('st'):
            server_type = server_type.replace('st_', '')
            data = self.filter_server_list(query, server_type, self.surf.st_servers)

        # regular connections
        else:
            data = self.filter_server_list(query, server_type, self.surf.reg_servers)
            
        # Show only first n servers (default 10)
        for server in data[0:self.max_server_entries]:
            items.append(
                ExtensionResultItem(
                    icon=Utils.get_path(f'images/flags/{server["flag_file"]}'),
                    name=server["country"] + " - " + server["city"],
                    highlightable=False,
                    on_enter=ExtensionCustomAction(
                        {
                            "action": "CONNECT_TO_SERVER",
                            "server": server["server_profile"],
                        }
                    ),
                )
            )
        return items
    
    # Returns server details object to which VPN is connected, if any
    def get_connection_status(self):
        return self.surf.get_status()


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        # Start with an empty options list
        items = []

        if not extension.surf.is_installed():
            items.append(
                ExtensionResultItem(
                    icon=Utils.get_path("images/icon.svg"),
                    name="Extension failed to load :/",
                    description="Make sure to have openvpn, wget, and unzip installed on system.",
                    highlightable=False,
                    on_enter=HideWindowAction(),
                )
            )
            return RenderResultListAction(items)

        # Check the arguments provided with ulauncher keyword - format: <keyword> <connect|disconnect|refreshdb> <connect-connect_type> <connect-server>
        argument = event.get_argument() or ""
        command, connection_type, server_query = (argument.split(" ", 2) + [None] + [None])[:3]
        
        if not command:
            # First selection page
            # Show Connect option only if no other openvpn connection is running
            server_connected = extension.get_connection_status()
            if server_connected:
                items.extend(
                    [
                        ExtensionResultItem(
                            icon=Utils.get_path(f'images/flags/{server_connected["flag_file"]}'),
                            name="Connected",
                            description=(server_connected["country"] + " - " + server_connected["city"] + " : " + server_connected["conn_type"]),
                            highlightable=False,
                            on_enter=SetUserQueryAction(
                                f'{extension.keyword or " "} '
                            ),
                        ),
                    ]
                )
            else:
                items.extend(
                    [
                        ExtensionResultItem(
                            icon=Utils.get_path("images/icon.svg"),
                            name="Connect",
                            description="Connect to Surfshark: choose from a list of servers",
                            highlightable=False,
                            on_enter=SetUserQueryAction(
                                f'{extension.keyword or " "} connect '
                            ),
                        ),
                    ]
                )
            
            items.extend(
                [
                    ExtensionResultItem(
                        icon=Utils.get_path("images/icon.svg"),
                        name="Disconnect",
                        description="Disconnect from Surfshark VPN",
                        highlightable=False,
                        on_enter=ExtensionCustomAction({"action": "DISCONNECT"}),
                    ),
                    ExtensionResultItem(
                        icon=Utils.get_path("images/icon.svg"),
                        name="Refresh DB",
                        description="Refresh Surfshark VPN connection database",
                        highlightable=False,
                        on_enter=ExtensionCustomAction({"action": "REFRESHDB"}),
                    ),
                ]
            )
        
        elif command in "connect":
            if not connection_type:
                # Connection type selection page
                for conn_type in Utils.get_available_connection_types():
                    items.append(
                        ExtensionResultItem(
                            icon=Utils.get_path("images/icon.svg"),
                            name=conn_type["name"],
                            description=conn_type["description"],
                            highlightable=False,
                            on_enter=SetUserQueryAction(
                                f'{extension.keyword or " "} connect {conn_type["action"]} '
                            ),
                        )
                    )
                
                
            else:
                # Server selection page
                server_list = extension.get_server_result_items(server_query, connection_type)
                if server_list:
                    items.extend(server_list)
                else:
                     items.extend(
                        [
                            ExtensionResultItem(
                                icon=Utils.get_path("images/icon.svg"),
                                name="No servers found with this criteria. :/",
                                description=(f"Try refreshing the server list."),
                                highlightable=False,
                                on_enter=SetUserQueryAction(
                                    f'{extension.keyword or " "} '
                                ),
                            ),
                        ]
                    )
                
        else:
            # invalid keyword sequence
            items.extend(
                [
                    ExtensionResultItem(
                        icon=Utils.get_path("images/icon.svg"),
                        name="Invalid selection.",
                        description=(f"Try again."),
                        highlightable=False,
                        on_enter=SetUserQueryAction(
                            f'{extension.keyword or " "} '
                        ),
                    ),
                ]
            )
        
        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        action = data["action"]

        if action == "CONNECT":
            return RenderResultListAction(extension.get_server_result_items())

        if action == "DISCONNECT":
            return extension.surf.disconnect()

        if action == "REFRESHDB":
            return extension.surf.refresh_openvpn_connections()

        if action == "CONNECT_TO_SERVER":
            return extension.surf.connect(data["server"])


class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.keyword = event.preferences["surf_kw"]
        try:
            extension.max_server_entries = int(event.preferences["surf_max_entry"])
        except ValueError:
            extension.max_server_entries = 10   # default to 10 entries


class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        if event.id == "surf_kw":
            extension.keyword = event.new_value
        # Another way could be to get the username and password in comma-separated way
        # Going with separate values to be more user-friendly
        if event.id == "surf_uname":
            extension.update_username(event.new_value)
        if event.id == "surf_passwd":
            extension.update_password(event.new_value)
        if event.id == "surf_max_entry":
            try:
                extension.max_server_entries = int(event.new_value)
            except ValueError:
                extension.max_server_entries = 10   # default to 10 entries

if __name__ == "__main__":
    SurfExtension().run()
