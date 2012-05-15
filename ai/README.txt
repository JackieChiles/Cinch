Instructions for adding AI modules

1) Copy the 'demo' folder within this directory. Rename it to suit your needs.

2) Open core.py. Replace the file contents with your AI Agent class implementation and save the file. Feel free to add other files that core.py happens to import.

3) Open your new folder and open __init__.py. Update the following information:
	- agent_classname
	- all the triple-underline items (author, version, date, skill, etc.)
	- nothing else!

4) Save __init__.py.

5) Add your own documentation, data files, etc. that are useful/needed for your AI Agent.

6) Do not edit any files outside of your new directory. The AI Manager will automatically find your new agent.

--------------------------

Notes:

You can test your module on its own, with effort. From the `ai` directory, run

`python -m MODULE_DIRECTORY`

where MODULE_DIRECTORY is the folder name of your module. This will initialize the agent
and open the daemon pipeline. Here you can start or kill the agent; see ai/base.py:handle_daemon_command() for details. For detailed testing, kill the agent
with the shutdown command, then create a new one using Python commands (e.g. `a = Agent()`) and do your testing from there.

A better testing method is welcome; import paths make this a challenge.




 
