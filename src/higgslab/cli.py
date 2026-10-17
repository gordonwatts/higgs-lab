"""One-command tutorial entry points, also usable on Windows without Bash."""
import argparse
import json
import sys
from pathlib import Path

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='instructor':
        from .instructor import main as instructor_main
        return instructor_main(argv[1:])
    p=argparse.ArgumentParser(prog='higgslab')
    sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run'); r.add_argument('dataset'); r.add_argument('output'); r.add_argument('--model')
    g=sub.add_parser('generate'); g.add_argument('output'); g.add_argument('--seed',type=int,default=42); g.add_argument('--mu',type=float,default=1); g.add_argument('--beta',type=float,default=1)
    c=sub.add_parser('check'); c.add_argument('--dataset',default='datasets/public'); c.add_argument('--output',default='output/check'); c.add_argument('--submission',default='submission')
    t=sub.add_parser('train'); t.add_argument('dataset'); t.add_argument('output'); t.add_argument('--mode',choices=['classifier','frozen','finetuned'],default='classifier'); t.add_argument('--epochs',type=int,default=4)
    sl=sub.add_parser('submission-line'); sl.add_argument('--repo'); sl.add_argument('--team')
    sc=sub.add_parser('score-local'); sc.add_argument('--output',default='output/suite'); sc.add_argument('--count',type=int,default=12); sc.add_argument('--seed',type=int,default=71); sc.add_argument('--model'); sc.add_argument('--submission')
    args=p.parse_args(argv)
    from .data import generate_dataset,load_dataset,checksums
    from .pipeline import run
    if args.command=='run':
        result=run(args.dataset,args.output,args.model)
        print(json.dumps(result,indent=2))
    elif args.command=='generate':
        truth=generate_dataset(args.output,args.seed,args.mu,args.beta)
        print(json.dumps({'public_local_truth':truth}))
    elif args.command=='train':
        from .training import train
        print(train(args.dataset,args.output,args.mode,args.epochs))
    elif args.command=='score-local':
        from .local import score_local
        print(json.dumps(score_local(args.output,args.count,args.seed,args.model,args.submission),indent=2))
    elif args.command=='submission-line':
        from .submission import submission_line
        print(submission_line(args.repo,args.team))
    elif args.command=='check':
        load_dataset(args.dataset)
        expected=Path(args.dataset)/'checksums.json'
        if expected.exists() and json.loads(expected.read_text())!=checksums(args.dataset):
            raise ValueError('dataset checksum mismatch')
        a=run(args.dataset,Path(args.output)/'first')
        b=run(args.dataset,Path(args.output)/'second')
        if a!=b:
            raise ValueError('non-deterministic result')
        from .check import check_submission
        check_submission(args.submission,args.dataset,Path(args.output)/'submission')
        print('PASS: dataset integrity, result contract, starter and deterministic second run')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
