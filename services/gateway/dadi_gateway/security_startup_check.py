

    env_mode = os.getenv('DADI_ENV','dev').strip().lower()
    provider = os.getenv('DADI_SIGNING_PROVIDER','').strip().lower()
    if env_mode in ('prod','production'):
        if provider != 'aws_kms':
            raise RuntimeError('In production mode (DADI_ENV=prod), DADI_SIGNING_PROVIDER must be aws_kms')
    else:
        if provider not in ('aws_kms','dev_ed25519',''):
            raise RuntimeError('Unsupported DADI_SIGNING_PROVIDER in dev mode')
