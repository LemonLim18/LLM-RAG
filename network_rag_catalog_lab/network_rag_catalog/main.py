# The main executable, import the pipeline.py orchestrator
import sys
# sys module is used to access the command-line arguments passed when executing the script
from app.pipeline import run

# The following code line means Only execute the following code if this file is being run directly (not imported as a module in another script)
# If runnnimg python main.py, the __name__ variable is somehow set to '__main__', and the code block under this if statement will be executed.
# If this file is imported as a module in another script, like "import main" inside the other.py, then the __name__ variable will be set to 'main', and the code block under this if statement will not be executed.
if __name__=='__main__':
    # if len(sys.argv)>1:
        # prompt = ' '.join(sys.argv[1:])
    # else:
        # prompt = input('Network operation request: ')
    # if no arguments passed (python main.py), prompt is set to the user input.
    
    # If got more than one argument (python main.py arg1 arg2 ...), prompt is set to the concatenation of all arguments as prompt.
    prompt=' '.join(sys.argv[1:]) if len(sys.argv)>1 else input('Network operation request: ')
    # Local test target. Change to R2/R3 or extend the list for multi-vendor tests.
    run(prompt,['R1'])


