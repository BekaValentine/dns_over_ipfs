import json
import subprocess
import sys
import uuid


def shell(*parts):
    return str(subprocess.check_output(parts), encoding='ascii')


class IPFS(object):
    def __init__(self, data_path):
        self.data_path = data_path
        while self.data_path[-1] == '/':
            self.data_path = self.data_path[:-1]

    # store content
    # object -> cid
    def store_content(self, obj):
        # ipfs add $OBJPATH
        file_name = uuid.uuid4().hex
        file_path = f'{self.data_path}/temp_{file_name}'
        json_rep = json.dumps(obj)
        with open(file_path, 'w') as f:
            f.write(json_rep)
        res = shell('ipfs', 'add', file_path)
        cid = res.split()[1]
        shell('rm', file_path)
        return cid

    # load content
    # cid -> maybe object
    def load_content(self, cid):
        # ipfs get --output $PATH /ipfs/$CID
        file_name = uuid.uuid4().hex
        file_path = f'{self.data_path}/temp_{file_name}'
        shell('ipfs', 'get', '--output', file_path, f'/ipfs/{cid}')
        with open(file_path, 'r') as f:
            res = f.read()
        shell('rm', file_path)
        return json.loads(res)

    # generate new key
    # name -> bool
    def generate_new_key(self, name):
        # ipfs key gen --type=rsa --size=2048 mykey
        res = shell('ipfs', 'key', 'gen', '--type=rsa',
                    '--size=2048', name)
        return 'Error' == res[0:5]

    # get the name for a key
    # key -> name
    def name_for_key(self, key):
        # ipfs key list -l
        res = shell('ipfs', 'key', 'list', '-l')
        for l in res.split('\n'):
            [key2, name] = l.strip().split()
            if key2 == key:
                return name

    # get the key for a name
    # name -> key
    def key_for_name(self, name):
        # ipfs key list -l
        res = shell('ipfs', 'key', 'list', '-l')
        for l in res.split('\n'):
            [key, name2] = l.strip().split()
            if name2 == name:
                return key

    # publish content id to name
    # cid, name -> ()
    def publish_content_id_to_name(self, cid, name):
        # ipfs name publish --key=$NAME /ipfs/$CID
        shell('ipfs', 'name', 'publish', f'--key={name}', f'/ipfs/{cid}')

    # publish content id to name
    # cid, name -> ()
    def publish_content_id_to_key(self, cid, key):
        # ipfs name publish --key=$NAME /ipfs/$CID
        self.publish_content_id_to_name(cid, self.name_for_key(key))

    # publish content to name
    # object, name -> ()
    def publish_content_to_name(self, obj, name):
        cid = self.store_content(obj)
        self.publish_content_id_to_name(cid, name)

    # retrieve content id for key
    # key -> maybe cid
    def retrieve_content_id_for_key(self, key):
        return shell('ipfs', 'name', 'resolve', key).strip()[6:]

    # retrieve content id for name
    # name -> maybe cid
    def retrieve_content_id_for_name(self, name):
        return self.retrieve_content_id_for_key(self.key_for_name(name))

    # retrieve content for name
    # name -> maybe obj
    def retrieve_content_for_name(self, name):
        return self.load_content(self.retrieve_content_id_for_name(name))

    # retrieve content for a key
    # key -> maybe cid
    def retrieve_content_for_key(self, key):
        return self.load_content(self.retrieve_content_id_for_key(key))

    # resolve a DNS lookup
    # domain name -> leaf records
    def resolve_dns_lookup(self, domain_name):
        domains = list(reversed(domain_name.split('.')))
        local_root = 'k2k4r8nk7wv8kbapvrfpleun1juxvmdv5vmuxpu57n371ygf0opljtdd'
        for domain in domains:
            print(
                f'Looking up {domain} at {self.name_for_key(local_root)} = {local_root}')
            local_root_info = self.retrieve_content_for_key(local_root)
            if domain not in local_root_info:
                print(
                    f'Domain {domain} not found in {self.name_for_key(local_root)} = {local_root}')
                return None
            if isinstance(local_root_info[domain], str):
                print(f'Found: {local_root_info[domain]}')
                local_root = local_root_info[domain]
            else:
                print(f'Error: {local_root_info} / {domain_name} / {domain}')
                return None
        print(
            f'Looking up A record at {self.name_for_key(local_root)} = {local_root}')
        leaf_info = self.retrieve_content_for_key(local_root)
        if 'A' in leaf_info:
            ip_addr = leaf_info['A']
            print(f'FOUND IP ADDRESS: {ip_addr}')
            return ip_addr
        return None


if __name__ == '__main__':
    data_path = sys.argv[1]
    print(f'Using data path: {data_path}')

    ipfs = IPFS(data_path)

    print(ipfs.resolve_dns_lookup('www.google.com'))
