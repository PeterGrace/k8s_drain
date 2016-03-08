k8s_drain
===============
This is an installable python cli app that will automate the process of draining a kubernetes node.  The app sets the node to unschedulable and then deletes the pods living on the node.

Assumptions
============
  - You use replication controllers to orchestrate your pod lifecycle,
  - You want to be able to script node drains in an automatable way

Installation
==============
  1. `git clone https://github/PeterGrace/k8s_drain`
  2. `cd k8s_drain`
  3. `pip install .`
  4. `k8s_drain --help`

Environment Variables
=====================
Don't like specifying user/password credentials via command line arguments?  Me either, that's why I have all of the variables also settable via environment variables:
  - K8SDRAIN_MASTER = url of the api server, without final slash
  - K8SDRAIN_USER = the username we should use to auth against the api server
  - K8SDRAIN_PASSWORD = the password we should use to auth against the api server
  - K8SDRAIN_REVERSE = should we reverse the process (make the node re-schedulable?) True/False.
  
  
  
