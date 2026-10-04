import json

import plotly.graph_objects as go

COLORS = ['#147d64', '#67ba98', '#2d5263', '#d4ab59', '#869ab0', '#bcd9c9']


def chart(figure, height=310):
    figure.update_layout(
        template='plotly_white',
        height=height,
        margin=dict(l=12, r=12, t=12, b=28),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif', color='#65736d', size=11),
        colorway=COLORS,
        legend=dict(orientation='h', y=-0.14),
        hovermode='x unified',
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor='#edf1ee', zeroline=False)
    return json.loads(figure.to_json())


def line_chart(frame, currency):
    f = go.Figure()
    if not frame.empty:
        f.add_trace(
            go.Scatter(
                x=[str(d) for d in frame.index],
                y=frame.value.tolist(),
                mode='lines',
                name=f'Value ({currency})',
                line=dict(color=COLORS[0], width=2.5),
                fill='tozeroy',
                fillcolor='rgba(20,125,100,.07)',
            )
        )
    return chart(f)


def allocation_chart(snap):
    names = [h['asset'].name for h in snap['holdings']] + ['Cash']
    values = [float(h['value']) for h in snap['holdings']] + [float(snap['cash'])]
    f = go.Figure(
        go.Pie(
            labels=names,
            values=values,
            hole=0.76,
            marker=dict(colors=COLORS, line=dict(color='white', width=3)),
            textinfo='none',
            hovertemplate='%{label}<br>%{percent}<extra></extra>',
            sort=False,
        )
    )
    f.update_layout(
        showlegend=False,
        annotations=[
            dict(
                text=f'<b>{len(snap["holdings"])}</b><br>holdings',
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=19, color='#1c3429'),
            )
        ],
    )
    return chart(f, 250)
