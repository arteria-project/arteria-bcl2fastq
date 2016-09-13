# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "puppetlabs/centos-7.0-64-puppet"
  config.vm.hostname = "arteria-bcl2fastq-dev"

  config.vm.provider "virtualbox" do |vb|  
    # Customize the amount of memory on the VM:
    vb.memory = "4000"
  end

  config.vm.provision "shell", inline: <<-SHELL
    sudo yum install -y epel-release
    sudo yum update
    sudo yum install -y unzip python-pip python-virtualenv git gcc-c++
    wget ftp://webdata2:webdata2@ussd-ftp.illumina.com/downloads/software/bcl2fastq/bcl2fastq2-v2.17.1.14-Linux-x86_64.zip
    unzip bcl2fastq2-v2.17.1.14-Linux-x86_64.zip
    sudo yum install -y bcl2fastq2-v2.17.1.14-Linux-x86_64.rpm
  SHELL
end
