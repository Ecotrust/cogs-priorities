Vagrant::Config.run do |config|

  config.vm.define "dev" do |dev|
    # dev.vm.box = "precise64"
    # dev.vm.box_url = "http://files.vagrantup.com/precise64.box"
    # based on the precise64 box but the expensive updates have already been done
    dev.vm.box = "precise64-custom"
    dev.vm.box_url = "http://labs.ecotrust.org/vagrant_boxes/precise64-custom.box"
    
    dev.vm.customize [
            'modifyvm', :id,
            "--memory", 768,
            "--cpus", 2]
    # ssh defaults to 2222
    dev.vm.forward_port 80, 8080
    dev.vm.forward_port 8000, 8000
    dev.vm.share_folder "v-app", "/usr/local/apps/cogs-priorities", "./"
  end

  # The stage server will NOT have a shared folder 
  # so we can test git deploys, etc that dont apply to the local dev box
  # We never ever, ever ssh into this box... it will be managed solely through ansible
  #  just as the production server will be
  config.vm.define "stage" do |stage|
    stage.vm.box = "precise64-custom"
    stage.vm.box_url = "http://labs.ecotrust.org/vagrant_boxes/precise64-custom.box"
    stage.vm.customize [
            'modifyvm', :id,
            "--memory", 768,
            "--cpus", 2]
    stage.vm.forward_port 80, 9080
    stage.vm.forward_port 8000, 9000
    # no shared folder
  end

  # deployment done directly with ansible, see deploy/*.sh
end
