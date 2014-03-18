Vagrant::Config.run do |config|
  config.vm.box = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"
  config.vm.customize ["modifyvm", :id, "--cpus", 2]
  config.vm.customize ["modifyvm", :id, "--memory", 898]

  # ssh defaults to 2222
  config.vm.forward_port 80, 8080
  config.vm.forward_port 8000, 8000
  config.vm.share_folder "v-app", "/usr/local/apps/cogs-priorities", "./"

  # deployment done directly with ansible, see deploy/*.sh
end
