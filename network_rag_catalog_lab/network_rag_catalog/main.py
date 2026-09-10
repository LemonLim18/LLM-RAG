import sys
from app.pipeline import run

if __name__=='__main__':
    prompt=' '.join(sys.argv[1:]) if len(sys.argv)>1 else input('Network operation request: ')
    # Local test target. Change to R2/R3 or extend the list for multi-vendor tests.
    run(prompt,['R1'])
