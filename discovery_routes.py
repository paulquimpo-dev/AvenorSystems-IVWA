"""Explicit, inert routes matching common.txt; never map names to local files."""
REDIRECTS = {
    '/help': '/support',
    '/services': '/products',
    '/company': '/about',
    '/team': '/about',
    '/partners': '/contact',
    '/press': '/news',
    '/resources': '/docs',
}

RESTRICTED = (
    '/.git/HEAD', '/.htaccess', '/.htpasswd', '/.ssh', '/.config',
    '/_backup', '/_private', '/config', '/database', '/backups',
    '/logs', '/includes', '/server-status',
)
