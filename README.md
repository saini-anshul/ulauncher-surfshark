# ulauncher-surfshark

## **Quickly connect to and disconnect from _SurfShark VPN_ from Ulauncher.**

> Uses OpenVPN to connect to SurfShark VPN profiles

> Download and refresh server profiles from https://my.surfshark.com/vpn/api/v1/server/configurations

> Connect to different types of VPN servers: Regular, Static-IP, or Multipoint; using UDP or TCP 

> Quikly search and connect to a specific VPN server based on _Country_ or _City_ name


## Requirements

- [Ulauncher 5](https://ulauncher.io/)
- Python >= 3
- openvpn
- wget
- unzip
- pkexec
- pgrep
- xargs
- awk


## How to add extension to Ulauncher

1. Open Ulauncher --> preferences

![Ulauncher preferences](/images/screenshots/howto/ulauncher-preferences.png)

2. Go to _Extensions_ tab

![Ulauncher extensions tab](/images/screenshots/howto/ulauncher-extensions.png)

3. Press _Add Extensions_ option

![Ulauncher add extensions](/images/screenshots/howto/ulauncher-add-extension.png)

4. Paste the following URL and press _Add_:

```
https://github.com/saini-anshul/ulauncher-surfshark
```

## Usage

Default keyword to trigger this extension is **`surf`**. This can be changed in the preferences.

![Basic commands](/images/screenshots/commands.png)

### Initial setup

The extension uses SurfShark's service credentials to connect to VPN servers, which can be found on the [Manual Setup Page](https://my.surfshark.com/vpn/manual-setup/main)

Provide the service credentials using extensions settings page.

![Extension Settings Page](/images/screenshots/extension_settings.png)


### Refreshing SurfShark VPN Server Profiles

The extension need to download SurfShark VPN connection profile database before connection to a VPN server can be established. This can be done by selecting the "**_Refresh DB_**" option.

![Refresh VPN Profile DB](/images/screenshots/refresh_db_main.png)

### Connecting to VPN

To connect to a VPN, select "**_Connect_** followed by the type of connection (UDP in most cases).

![Connect option](/images/screenshots/commands.png)

![Connection Types List](/images/screenshots/connection_types.png)

Once connection type is selected, a list with available server profiles for that connection type is shown. By default, total number of servers displayed in the list is 10, which can be changed in the extention settings.

![Server List](/images/screenshots/server_list.png)

The extension allows searching for a specific server by _Country_ or by _City_ name.

![Filtered Server List - TO](/images/screenshots/server_search_to.png)

![Filtered Server List - US](/images/screenshots/server_search_us.png)

Select the desired server and provide password for extension to connect to the selected server using OpenVPN with admin privileges.

### Connection Status

Once connected to a server, simply launch the extension to check on the status of VPN connection and server details.

![Server Status and Connection Details](/images/screenshots/connection_details.png)

### Disconnect

To disconnect from VPN server, launch extention using keyword and choose **_Disconnect_** option. 

![Disconnect Option](/images/screenshots/disconnect_server.png)

## License

[MIT](LICENSE)
