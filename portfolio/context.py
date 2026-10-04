def workspace(request):
    if not request.user.is_authenticated:
        return {}
    portfolios = request.user.portfolio_set.order_by('id')
    active = portfolios.filter(id=request.session.get('portfolio_id')).first() or portfolios.first()
    return {'workspaces': portfolios, 'active_portfolio': active}
