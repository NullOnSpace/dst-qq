from config import ADMINS

perms = {
    'admin': ADMINS,
}


def check_permission(perm):
    perm_members = perms[perm]
    def decorator(fn):
        async def _(session, *args, **kwargs):
            user_id = session.ctx['user_id']
            if user_id in perm_members:
                rt = await fn(session, *args, **kwargs)
                return rt
            else:
                await session.send("权限不足")
        return _
    return decorator