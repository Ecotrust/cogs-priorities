
Initial provisioning of ALL servers defined in hosts

	ansible-playbook provision.yml -i ./hosts


Provision only the staging server

	ansible-playbook provision.yml -i ./hosts -v --limit stage


Provision on a server that requires passwords for sudo and ssh
	
	ansible-playbook provision.yml -i ./hosts --ask-sudo-pass --ask-pass --limit <host>


Only run a subset of the provisioning tasks. For example, deploy the latest master branch to production

	ansible-playbook provision.yml -i ./hosts -v --tags deploy --limit <host>

Just **restart services**

	ansible-playbook provision.yml -i ./hosts -v --tags restart --limit <host>

When we want to trigger a **re-import of the dataset**

    ansible-playbook provision.yml -i ./hosts -v --tags restart -e "newdata=true" --limit <host>


