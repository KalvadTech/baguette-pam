# PAM module for Baguette (CIBA) 

## Installation (Ubuntu 22.04)

Read before copy-paste
```
apt install python python-requests python-qrcode libpam-python
mkdir /lib/security
cp src/pam_baguette.py /lib/security/
vim /etc/pam_baguette/config.yml
```
See `example_config.yml`

## Example Configuration (SSH, Ubuntu 22.04)
```
vim /etc/pam.d/sshd
```
edit
```
    auth required pam_python.so pam_baguette.py /etc/pam_baguette/config.yml
```
```
vim /etc/ssh/sshd_config
```
edit
```
    PermitRootLogin yes
    RSAAuthentication no
    PubkeyAuthentication no
    PasswordAuthentication no
    ChallengeResponseAuthentication yes
    UsePAM yes
```
```
systemctl restart sshd
```
## Development

### Instalation (Ubuntu 16.04)
```
apt install pamtester
```
### Configuration (Ubuntu 16.04)
```
vim /etc/pam.d/pamtester
```
create
```
    auth required pam_python.so pam_baguette.py
```

### Deploy
```
cp src/pam_baguette.py /lib/security/
```
### Test
```
pamtester -v pamtester username authenticate
```
