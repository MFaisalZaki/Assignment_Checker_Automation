import jenkins
import json
import ConfigParser
import time
import os
import sys

# Script calling convention:
# python script.py <course_name> <mode> <..>,
# Where mode : deploy_repo no extra arugments needed
# Where mode : upload_template then followed by assignment name and assignment template path
# Where mode : execute_test then followed by assignment name and test cases path
#              if it followed by any flag will execute the tests but won't commit any code

# Read user configuration file ini
usr_cfg = ConfigParser.ConfigParser()
# ToDo: a predefined path for configuration should be provided
usr_cfg.read('python_ini.ini')

# Connect to Jenkins
server = jenkins.Jenkins(usr_cfg.get('Jenkins_Parameters','Server_Link'), \
                         usr_cfg.get('User_Parameters','Username'),       \
                         usr_cfg.get('User_Parameters','Password'))

# Read job configuration parameters JSON file.
with open(usr_cfg.get('Students_Info','Students_file')) as job_cfg_parameters:
    job_cfg_params = json.load(job_cfg_parameters);
    job_cfg_parameters.close()

# Get Jenkins job name.
jenkins_job_name = usr_cfg.get('Jenkins_Parameters','Job_Name')

# ToDo: Add here the option for Jenkins job creation.

# Execute job for each student
for job in job_cfg_params:
    try:

        #Configure all parameters which are fixed for all students
        job['STUDENT_INIT_REPO']              = 'true' if ("deploy_repo"     == sys.argv[2])  and (not '' == sys.argv[1]) else 'false'
        job['UPLOAD_NEW_ASSIGNMENT_TEMPLATE'] = 'true' if ("upload_template" == sys.argv[2])  and (len(sys.argv) >= 4) else 'false'
        job['EXECUTE_TEST']                   = 'true' if ("execute_test"    == sys.argv[2])  and (len(sys.argv) >= 4) else 'false'
        job['ASSIGNMENT_NAME']                = sys.argv[3] if(("execute_test" == sys.argv[2]) or ("upload_template" == sys.argv[2])) and (len(sys.argv) >= 5) else ''
        job['NEW_ASSIGNMENT_TEMPLATE_PATH']   = sys.argv[4] if(("upload_template" == sys.argv[2])) and (len(sys.argv) >= 5) else ''
        job['TEST_CASE_REPO_LOCAL_PATH']      = sys.argv[4] if(("execute_test" == sys.argv[2])) and (len(sys.argv) >= 5) else ''
        job['LOG_FOLDER_NAME']                = usr_cfg.get('Jenkins_Parameters','Log_Folder_Name')
        job['RESULTS_FOLDER_NAME']            = usr_cfg.get('Jenkins_Parameters','Results_Folder_Name')
        job['COURSE_NAME']                    = sys.argv[1] if (len(sys.argv) >= 2) else ''
        job['UPLOAD_JOB_RESULTS']             = 'false'
        job['STUDENT_REPO_NAME']              = usr_cfg.get('Jenkins_Parameters','Main_Repo_Name')
        job['BASH_TESTING_SCRIPT']            = usr_cfg.get('Test_Env','Test_Script_File')
        job['BASH_TESTING_SCRIPT_PATH']       = usr_cfg.get('Test_Env','Test_Script_Path')

        # job['STUDENT_INIT_REPO']              = 'true' if ("deploy_repo" in sys.argv) else 'false'
        # job['UPLOAD_NEW_ASSIGNMENT_TEMPLATE'] = 'true' if (not "deploy_repo" in sys.argv) and ("upload_template" in sys.argv) else 'false'
        # job['EXECUTE_TEST']                   = 'true'  if (not "deploy_repo" in sys.argv) and ("execute_test" in sys.argv) else 'false'
        # job['ASSIGNMENT_NAME']                = 'RightAngle'
        # job['LOG_FOLDER_NAME']                = 'Console_Logs'
        # job['RESULTS_FOLDER_NAME']            = 'Test_Results'
        # job['COURSE_NAME']                    = '2016_2017_DSP'
        # job['UPLOAD_JOB_RESULTS']             = 'false'


        # Get last build number to be able to wait for the next build to finish.
        last_build_num = server.get_job_info(jenkins_job_name)['lastBuild']['number']

        # Start job build
        server.build_job(jenkins_job_name, job)

    except Exception as e: print str(e)
        # ToDo: Handle Jenkins exceptions.
    else:
        # Wait for the current build to finish.
        while True:
            curr_build_num = server.get_job_info(jenkins_job_name)['lastBuild']['number']
            build_info     = server.get_build_info(jenkins_job_name, curr_build_num)
            build_result   = server.get_build_info(jenkins_job_name, curr_build_num)['result']
            if (not build_info['building']) and (curr_build_num > last_build_num):
                break

        # Log data for failure in Jenkins execution jobs.
        # Note that we may encounter two possible scenarios for jobs failures
        #   1. Environment errors like no such directory, Github authentation errors ... etc
        #   2. Test cases failures
        # Simplest solution is to log the whole console for both failures and success,
        # But I don't like this approach which will make the overall automation stupid,
        # But we can log in case of Jenkins jobs Failures and force test cases to return
        # success and log there reults in another file which will be uploaded by default
        # back to test case results folder.
        # In case of failures then whole log will be uploaded back to student's repository
        # in a different folder.
        if (job['EXECUTE_TEST'] == 'true'):
            # It will be better to log the whole console for each job, Since
            # Jenkins log won't be available on the host for long.
            # File naming convention <STUDENT_ID>_<BUILD_NUMBER>_<DATE>.log
            log_file_name = job['STUDENT_ID'] + str(curr_build_num) + time.strftime("%x %X").replace("/","").replace(" ","_").replace(":","_")
            log_file_name = log_file_name.replace(" ","_")
            build_console = server.get_build_console_output(jenkins_job_name, curr_build_num).replace(usr_cfg.get('User_Parameters','Username'), " ")
            log_file = usr_cfg.get('Jenkins_Parameters','Job_Pwd')
            log_file += usr_cfg.get('Jenkins_Parameters','Job_Name')
            log_file += "/workspace"             + "/"
            log_file += job['STUDENT_REPO_NAME'] + "/"
            log_file += job['COURSE_NAME']       + "/"
            log_file += job['ASSIGNMENT_NAME']   + "/"
            log_file += job['LOG_FOLDER_NAME']   + "/"
            log_file += (log_file_name + ".txt")

            with open(log_file, "w") as f:
                f.write(build_console)
                f.close()

            # Trigger another job for test cases upload, I don't like this approach but
            # it the shortest path I can figure out now.
            # Start job build
            job['UPLOAD_JOB_RESULTS'] = 'true' if (("execute_test" == sys.argv[2]) and (len(sys.argv) == 5)) else 'false'
            server.build_job(jenkins_job_name, job)

            # Get last build number to be able to wait for the next build to finish.
            last_build_num = server.get_job_info(jenkins_job_name)['lastBuild']['number']

            # Wait for the current build to finish.
            while True:
                curr_build_num = server.get_job_info(jenkins_job_name)['lastBuild']['number']
                build_info     = server.get_build_info(jenkins_job_name, curr_build_num)
                build_result   = server.get_build_info(jenkins_job_name, curr_build_num)['result']
                if (not build_info['building']) and (curr_build_num > last_build_num):
                    break
                else:
                    pass
        else:
            pass
