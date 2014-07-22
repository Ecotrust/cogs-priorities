Vagrant::Config.run do |config|

  config.vm.define "dev" do |dev|
    dev.vm.box = "trusty64"
    dev.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
    
    dev.vm.customize [
            'modifyvm', :id,
            "--memory", 1668,
            "--cpus", 2]
    # ssh defaults to 2222
    dev.vm.forward_port 80, 8080
    dev.vm.forward_port 8000, 8000
    dev.vm.share_folder "v-app", "/usr/local/apps/cogs", "./", owner:"www-data"
  end

  # The stage server will NOT have a shared folder 
  # so we can test git deploys, etc that dont apply to the local dev box
  # We never ever, ever ssh into this box... it will be managed solely through ansible
  #  just as the production server will be
  config.vm.define "stage" do |stage|
    stage.vm.box = "trusty64"
    stage.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
    stage.vm.customize [
            'modifyvm', :id,
            "--memory", 1668,
            "--cpus", 2]
    stage.vm.forward_port 80, 9080
    stage.vm.forward_port 8000, 9000
    # no shared folder
  end

  # deployment done directly with ansible, see deploy/*.sh
end
