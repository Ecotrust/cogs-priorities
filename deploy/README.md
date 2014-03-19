
Initial provisioning of ALL servers defined in hosts

	ansible-playbook provision.yml -i ./hosts


Provision only the staging server

	ansible-playbook provision.yml -i ./hosts -v --limit stage


Provision on a server that requires passwords for sudo and ssh
	
	ansible-playbook provision.yml -i ./hosts --ask-sudo-pass --ask-pass --limit stage


Only run a subset of the provisioning tasks. This is implemented as tags; complete list todo:

	ansible-playbook provision.yml -i ./hosts -v --limit stage --tags deploy
	ansible-playbook provision.yml -i ./hosts -v --limit stage --tags restart

*A special case*, define when we want to trigger a re-import of the dataset

    ansible-playbook provision.yml -i ./hosts -v --limit stage --tags newdata -extra-vars "newdata=true"


