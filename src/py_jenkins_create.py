import jenkins
import ConfigParser

# Read user configuration file ini
usr_cfg = ConfigParser.ConfigParser()
# ToDo: a predefined path for configuration should be provided
usr_cfg.read('python_ini.ini')

# Connect to Jenkins
server = jenkins.Jenkins(usr_cfg.get('Jenkins_Parameters','Server_Link'), \
                         usr_cfg.get('User_Parameters','Username'),       \
                         usr_cfg.get('User_Parameters','Password'))

# Read job configuration parameters XML file.
with open(usr_cfg.get('Jenkins_Parameters','Job_Cfg')) as job_cfg_parameters:
    job_cfg_params = job_cfg_parameters.read();
    job_cfg_parameters.close()
    server.create_job(usr_cfg.get('Jenkins_Parameters','Job_Name'), job_cfg_params)
    jobs = server.get_jobs()
