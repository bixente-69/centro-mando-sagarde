# -*- coding: utf-8 -*-
"""
PANEL DE OBRA — 9 secciones (capa 3)
-------------------------------------
Genera un panel HTML por obra con navegacion de pestanas:
  Panel · Trabajos · Materiales · Personal · Prioridades · Riesgos · Normativa · Documentos · Actualizar

Consume datos ya normalizados:
  historial   -> de motor_informes (avance/bloqueos)
  materiales  -> de lectores.leer_materiales
  ficha       -> de lectores.leer_ficha
  documentos  -> de lectores.listar_documentos

No sabe leer archivos: eso lo hacen los adaptadores/lectores. Aqui solo se
calcula y se pinta.
"""
import html as html_lib
import json
import os
from collections import OrderedDict
from datetime import datetime

import motor_informes as motor

ESTILOS = """
:root{
  --bg:#f4f6f9;--card:#fff;--header:#0b1f3a;--header2:#123a63;--text:#1c2733;
  --muted:#647184;--accent:#f5a524;--accent2:#2e7dd7;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;
  --radius:10px;--gap:16px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;}
.wrap{max-width:1320px;margin:0 auto;padding:18px;}
.header{background:linear-gradient(120deg,var(--header),var(--header2));color:#fff;border-radius:var(--radius);padding:20px 26px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;}
.header .brand{font-size:11.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);font-weight:700;}
.header h1{font-size:21px;font-weight:700;margin-top:2px;}
.header .sub{font-size:12.5px;color:#c7d3e3;margin-top:4px;}
.header .meta{text-align:right;font-size:12px;color:#c7d3e3;}
.header a.volver{color:#fff;text-decoration:none;font-size:12.5px;border:1px solid rgba(255,255,255,.35);padding:5px 11px;border-radius:6px;display:inline-block;margin-top:6px;}
.header a.volver:hover{background:rgba(255,255,255,.12);}
.nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;}
.nav button{border:none;background:#fff;color:var(--text);padding:9px 15px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.07);}
.nav button.active{background:var(--header);color:#fff;}
.view{display:none;}
.view.active{display:block;}
.banner{background:#fff4e5;border:1px solid var(--accent);color:#7a4c00;border-radius:var(--radius);padding:11px 16px;margin-bottom:14px;font-size:13px;}
.banner.bad{background:#fdecea;border-color:var(--bad);color:#7a231c;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:var(--gap);margin-bottom:var(--gap);}
.kpi{background:var(--card);border-radius:var(--radius);padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.07);}
.kpi .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}
.kpi .value{font-size:25px;font-weight:700;margin-top:5px;}
.kpi .hint{font-size:11.5px;color:var(--muted);margin-top:3px;}
.chart-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:var(--gap);margin-bottom:var(--gap);}
.card{background:var(--card);border-radius:var(--radius);padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:var(--gap);}
.card h3{font-size:14px;font-weight:700;margin-bottom:12px;}
.card canvas{max-height:300px;}
.table-scroll{overflow-x:auto;}
table.data{width:100%;border-collapse:collapse;font-size:13px;}
table.data thead th{text-align:left;padding:8px 10px;border-bottom:2px solid #e3e7ee;color:var(--muted);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
table.data tbody td{padding:8px 10px;border-bottom:1px solid #eef1f5;}
table.data tbody tr:hover{background:#f8f9fb;}
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;}
.badge.bad{background:#fdecea;color:var(--bad);}.badge.warn{background:#fff4e5;color:var(--warn);}.badge.ok{background:#e8f6ee;color:var(--ok);}
.badge.f1{background:#e8f0fc;color:#1a3a7a;}.badge.f3{background:#f0f0f0;color:#4a5568;}.badge.f4{background:#f5f5f5;color:#718096;}
.empty{color:var(--muted);font-size:13.5px;padding:16px 4px;}
.doc-cat{font-size:12px;font-weight:700;color:var(--header2);text-transform:uppercase;letter-spacing:.5px;margin:14px 0 6px;}
.doc a{color:var(--accent2);text-decoration:none;}.doc a:hover{text-decoration:underline;}
.norm li{margin:6px 0 6px 18px;font-size:13.5px;}
.footer{text-align:center;font-size:11.5px;color:var(--muted);padding:16px 0;}
.seccion-plegable{cursor:default;}
.seccion-plegable>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:14px;font-weight:700;padding:2px 0;}
.seccion-plegable>summary::-webkit-details-marker{display:none;}
.seccion-plegable>summary::after{content:'▸';color:var(--muted);font-size:12px;flex-shrink:0;}
.seccion-plegable[open]>summary::after{content:'▾';}
.seccion-plegable>.seccion-contenido{margin-top:12px;}
#sec-tareas,#sec-dudas,#sec-ejecucion,#sec-inv-bloqueado,#sec-inv-sin_revisar,
#sec-inv-viable,#sec-inv-otros_gremios,#sec-inv-dudas,#sec-inv-terminado,
#sec-preguntas-catalogo,#sec-prevision{display:none;}
.indice-nav{background:linear-gradient(120deg,var(--header),var(--header2));border-radius:var(--radius);padding:9px 14px;margin-bottom:var(--gap);display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.indice-nav-label{color:var(--accent);font-size:10.5px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;}
.indice-nav-grupo{position:relative;}
.indice-nav-grupo>summary{list-style:none;cursor:pointer;background:rgba(255,255,255,.14);color:#fff;padding:8px 14px;border-radius:7px;font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;}
.indice-nav-grupo>summary::-webkit-details-marker{display:none;}
.indice-nav-grupo>summary::after{content:'▾';font-size:10px;}
.indice-nav-grupo[open]>summary{background:rgba(255,255,255,.26);}
.indice-nav-panel{position:absolute;top:calc(100% + 8px);left:0;background:var(--card);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.2);padding:8px;min-width:260px;z-index:20;display:flex;flex-direction:column;gap:2px;}
.indice-nav-link{display:flex;justify-content:space-between;gap:10px;padding:8px 10px;border-radius:6px;font-size:13px;font-weight:600;color:var(--text);text-decoration:none;}
.indice-nav-link:hover{background:var(--bg);}
.bento-command{margin-bottom:var(--gap);}
.bento-health{background:var(--card);border:1px solid color-mix(in srgb,var(--muted) 24%,transparent);border-radius:var(--radius);padding:19px 21px;box-shadow:0 1px 3px color-mix(in srgb,var(--header) 8%,transparent);margin-bottom:var(--gap);}
.bento-health-top{display:flex;align-items:flex-start;justify-content:space-between;gap:22px;margin-bottom:16px;}
.bento-eyebrow{display:block;color:var(--accent2);font-size:10.5px;font-weight:800;letter-spacing:1.25px;text-transform:uppercase;margin-bottom:4px;}
.bento-health h2{font-size:18px;line-height:1.25;}.bento-health-meta{color:var(--muted);font-size:11.5px;margin-top:4px;}
.bento-health-side{display:flex;align-items:stretch;gap:12px;flex:0 0 auto;}
.bento-stat{min-width:126px;text-align:right;padding-left:13px;border-left:1px solid color-mix(in srgb,var(--muted) 24%,transparent);}
.bento-stat strong{display:block;color:var(--header);font-size:28px;line-height:1.05;}.bento-stat span{display:block;color:var(--muted);font-size:10.5px;margin-top:4px;}
.bento-attention{display:flex;flex-direction:column;justify-content:center;max-width:355px;padding:9px 12px;border-radius:8px;border:1px solid color-mix(in srgb,var(--warn) 34%,transparent);background:color-mix(in srgb,var(--warn) 8%,var(--card));color:var(--warn);}
.bento-attention.is-ok{border-color:color-mix(in srgb,var(--ok) 34%,transparent);background:color-mix(in srgb,var(--ok) 8%,var(--card));color:var(--ok);}
.bento-attention strong{font-size:11.5px;text-transform:uppercase;letter-spacing:.55px;}.bento-attention span{font-size:10.5px;line-height:1.35;margin-top:2px;color:var(--text);}
.bento-segments{display:flex;min-height:12px;border-radius:20px;overflow:hidden;background:color-mix(in srgb,var(--muted) 12%,var(--card));}
.bento-segment{display:block;min-width:0;}.bento-segment+.bento-segment{box-shadow:-2px 0 0 var(--card);}
.bento-legend{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-top:11px;}
.bento-legend-item{text-align:center;min-width:0;}.bento-legend-label{display:flex;align-items:center;justify-content:center;gap:6px;color:var(--muted);font-size:10.5px;line-height:1.2;}
.bento-dot{display:inline-block;width:8px;height:8px;border-radius:50%;flex:0 0 auto;background:var(--bento-color);}.bento-legend-item strong{display:block;color:var(--bento-color);font-size:17px;margin-top:3px;}
.bento-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-auto-rows:minmax(126px,auto);gap:var(--gap);}
.bento-link{color:inherit;text-decoration:none;}.bento-card{--bento-color:var(--muted);display:flex;flex-direction:column;min-width:0;background:var(--card);border:1px solid color-mix(in srgb,var(--muted) 24%,transparent);border-left:4px solid var(--bento-color);border-radius:var(--radius);padding:18px 20px;box-shadow:0 1px 3px color-mix(in srgb,var(--header) 8%,transparent);transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease;}
.bento-card:hover,.bento-chip:hover{transform:translateY(-1px);box-shadow:0 7px 20px color-mix(in srgb,var(--header) 11%,transparent);border-color:var(--bento-color);}
.bento-card:focus-visible,.bento-chip:focus-visible{outline:3px solid color-mix(in srgb,var(--accent2) 35%,transparent);outline-offset:2px;}
.bento-hero{grid-column:span 8;grid-row:span 2;--bento-color:var(--ok);padding:22px 24px;}
.bento-small{grid-column:span 4;}.bento-half{grid-column:span 6;}
.bento-card-kicker{display:flex;align-items:center;gap:7px;color:var(--bento-color);font-size:10.5px;font-weight:800;letter-spacing:.75px;text-transform:uppercase;}
.bento-card h3{font-size:15px;margin-top:8px;}.bento-hero h3{font-size:23px;margin-top:7px;}.bento-card-copy{color:var(--muted);font-size:11.5px;margin-top:3px;}
.bento-number{color:var(--bento-color);font-size:38px;font-weight:800;line-height:1;margin-top:auto;padding-top:12px;}.bento-number-label{color:var(--muted);font-size:10.5px;margin-top:4px;}
.bento-hero-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;}.bento-hero-total{text-align:right;flex:0 0 auto;}.bento-hero-total strong{display:block;color:var(--ok);font-size:44px;line-height:1;}.bento-hero-total span{display:block;color:var(--muted);font-size:10.5px;margin-top:4px;}
.bento-breakdown{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:auto;padding-top:20px;}.bento-breakdown-item{--bento-color:var(--muted);padding:13px 14px;border:1px solid color-mix(in srgb,var(--bento-color) 24%,transparent);border-radius:8px;background:color-mix(in srgb,var(--bento-color) 6%,var(--card));}.bento-breakdown-item span{display:block;color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.45px;}.bento-breakdown-item strong{display:block;color:var(--bento-color);font-size:26px;line-height:1.1;margin-top:4px;}
.bento-reference{margin-top:var(--gap);padding:16px 18px;border:1px solid color-mix(in srgb,var(--muted) 24%,transparent);border-radius:var(--radius);background:color-mix(in srgb,var(--muted) 5%,var(--card));}.bento-reference-title{color:var(--muted);font-size:10.5px;font-weight:800;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}.bento-chips{display:flex;flex-wrap:wrap;gap:8px;}
.bento-chip{--bento-color:var(--muted);display:inline-flex;align-items:center;gap:8px;padding:8px 12px;background:var(--card);border:1px solid color-mix(in srgb,var(--muted) 25%,transparent);border-left:3px solid var(--bento-color);border-radius:8px;color:var(--text);font-size:12px;font-weight:650;text-decoration:none;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease;}
.grupo-etiqueta{font-size:10.5px;font-weight:700;letter-spacing:.5px;color:var(--muted);text-transform:uppercase;margin:18px 2px 8px;}
.timeline-prio{position:relative;}
.timeline-item{position:relative;display:grid;grid-template-columns:50px minmax(0,1fr);gap:15px;padding-bottom:16px;}
.timeline-item::before{content:"";position:absolute;left:24px;top:48px;bottom:-2px;width:2px;background:color-mix(in srgb,var(--muted) 28%,transparent);}
.timeline-item.last-visible::before{display:none;}
.timeline-item[hidden]{display:none;}
.timeline-node{position:relative;z-index:2;width:50px;height:50px;display:grid;place-items:center;border-radius:50%;color:var(--card);font-size:17px;font-weight:800;box-shadow:0 4px 12px color-mix(in srgb,var(--header) 18%,transparent);}
.timeline-node.ok{background:var(--ok);}.timeline-node.warn{background:var(--warn);}
.task-card{min-width:0;background:var(--card);border-radius:var(--radius);border:1px solid color-mix(in srgb,var(--muted) 20%,transparent);border-left:4px solid var(--ok);box-shadow:0 1px 3px color-mix(in srgb,var(--header) 8%,transparent);overflow:hidden;transition:box-shadow .2s ease,border-color .2s ease;}
.task-card.warn{border-left-color:var(--warn);}
.task-card:hover,.task-card[open]{box-shadow:0 7px 22px color-mix(in srgb,var(--header) 12%,transparent);}
.task-card>summary{position:relative;display:block;list-style:none;cursor:pointer;padding:16px 46px 16px 18px;}
.task-card>summary::-webkit-details-marker,.more-locations>summary::-webkit-details-marker{display:none;}
.task-card>summary::marker,.more-locations>summary::marker{content:"";}
.task-card>summary:focus-visible{outline:3px solid color-mix(in srgb,var(--accent2) 35%,transparent);outline-offset:-3px;}
.summary-topline,.summary-titleline,.compact-bottom,.progress-wrap{display:flex;align-items:center;min-width:0;}
.summary-topline{gap:9px;}.summary-titleline{justify-content:space-between;gap:14px;margin-top:9px;}
.task-meta,.scope{color:var(--muted);font-size:11.5px;}.task-meta{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.task-title{font-size:16px;font-weight:750;line-height:1.3;}.scope{flex:0 0 auto;}
.compact-bottom{display:grid;grid-template-columns:minmax(250px,.9fr) minmax(210px,1.1fr);gap:20px;margin-top:13px;}
.progress-wrap{gap:9px;}.progress-track{display:block;flex:1;height:8px;min-width:90px;background:color-mix(in srgb,var(--muted) 13%,var(--card));border-radius:20px;overflow:hidden;}
.progress-fill{display:block;height:100%;background:var(--ok);border-radius:inherit;}.task-card.warn .progress-fill{background:var(--warn);}
.progress-copy,.location-summary{font-size:11.5px;color:var(--muted);}.progress-copy{white-space:nowrap;}.location-summary{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.location-summary>span{color:var(--accent2);font-weight:800;}
.chevron{position:absolute;right:20px;top:21px;width:9px;height:9px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);transition:transform .2s ease;}
.task-card[open]>summary .chevron{transform:rotate(225deg);top:25px;}
.task-detail{padding:16px 18px 18px;border-top:1px solid color-mix(in srgb,var(--muted) 17%,transparent);background:color-mix(in srgb,var(--bg) 70%,var(--card));}
.stat-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:17px;}
.stat{padding:12px;text-align:center;background:var(--card);border:1px solid color-mix(in srgb,var(--muted) 20%,transparent);border-radius:8px;}
.stat strong{display:block;font-size:24px;line-height:1.1;}.stat span{display:block;margin-top:3px;color:var(--muted);font-size:11.5px;}
.stat.done strong{color:var(--ok);}.stat.pending strong{color:var(--warn);}.stat.total strong{color:var(--header2);}
.locations-block,.reason-block{padding:13px 14px;background:var(--card);border:1px solid color-mix(in srgb,var(--muted) 18%,transparent);border-radius:8px;}
.reason-block{margin-top:12px;}.secondary-reason{border-left:3px solid var(--accent2);}
.detail-heading,.location-group-head{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.detail-label{margin:0;color:var(--muted);font-size:10.5px;font-weight:800;letter-spacing:.55px;}
.location-legend{display:flex;align-items:center;gap:5px;margin:0;color:var(--muted);font-size:10.5px;}
.legend-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-left:5px;}.legend-dot.done{background:var(--ok);}.legend-dot.pending{background:var(--warn);}
.location-group{padding:11px 0;border-bottom:1px solid color-mix(in srgb,var(--muted) 14%,transparent);}
.location-group:last-child{border-bottom:0;padding-bottom:0;}.location-group-head{margin-bottom:7px;font-size:11.5px;}.location-group-head strong{font-size:12px;color:var(--header2);}.location-group-head span{color:var(--muted);}
.location-chips{display:flex;flex-wrap:wrap;gap:6px;}
.location-chip{display:inline-flex;align-items:center;gap:7px;padding:4px 5px 4px 8px;border:1px solid color-mix(in srgb,var(--muted) 24%,transparent);border-radius:7px;background:var(--card);font-size:11px;}
.location-chip.is-done{border-left:3px solid var(--ok);}.location-chip.is-pending{border-left:3px solid var(--warn);}
.chip-state{padding:1px 5px;border-radius:4px;color:var(--muted);background:color-mix(in srgb,var(--muted) 10%,var(--card));font-size:9.5px;font-weight:800;}
.is-done .chip-state{color:var(--ok);}.is-pending .chip-state{color:var(--warn);}
.more-locations{margin-top:10px;}.more-locations>summary{list-style:none;cursor:pointer;color:var(--accent2);font-size:12px;font-weight:700;padding:5px 0;}
.more-locations>summary::before{content:"+";display:inline-grid;place-items:center;width:18px;height:18px;margin-right:6px;border:1px solid currentColor;border-radius:50%;}
.more-locations[open]>summary::before{content:"−";}.more-locations-content{margin-top:2px;padding-left:12px;border-left:2px solid color-mix(in srgb,var(--accent2) 22%,transparent);}
.reason-block p:last-child{margin:5px 0 0;font-size:12.5px;}.technical-meta{margin:12px 2px 0;color:var(--muted);font-size:10.5px;}
@media(max-width:768px){.indice-nav-panel{left:0;right:0;min-width:0;}}
@media(max-width:768px){.header{flex-direction:column;}.kpi-row{grid-template-columns:repeat(2,1fr);}.chart-row{grid-template-columns:1fr;}}
@media(max-width:760px){
  .timeline-item{grid-template-columns:40px minmax(0,1fr);gap:10px;}.timeline-node{width:40px;height:40px;font-size:14px;}.timeline-item::before{left:19px;top:39px;}
  .task-card>summary{padding:14px 38px 14px 13px;}.chevron{right:15px;top:19px;}.task-card[open]>summary .chevron{top:23px;}
  .summary-titleline{align-items:flex-start;flex-direction:column;gap:2px;}.compact-bottom{grid-template-columns:1fr;gap:8px;}.progress-wrap{flex-wrap:wrap;}.progress-track{flex-basis:120px;}
  .task-meta{white-space:normal;}.location-summary{white-space:normal;}.task-detail{padding:13px;}.stat{padding:10px 5px;}.stat strong{font-size:20px;}
  .detail-heading{align-items:flex-start;flex-direction:column;gap:5px;}
}
@media(max-width:980px){.bento-legend{grid-template-columns:repeat(3,minmax(0,1fr));}.bento-hero{grid-column:span 12;grid-row:auto;}.bento-small,.bento-half{grid-column:span 6;}}
@media(max-width:640px){.bento-health-top,.bento-hero-head{flex-direction:column;}.bento-health-side{width:100%;flex-direction:column;}.bento-stat{text-align:left;border-left:0;border-top:1px solid color-mix(in srgb,var(--muted) 24%,transparent);padding:9px 0 0;}.bento-attention{max-width:none;}.bento-legend{grid-template-columns:repeat(2,minmax(0,1fr));}.bento-small,.bento-half{grid-column:span 12;}.bento-breakdown{grid-template-columns:1fr;}.bento-hero-total{text-align:left;}}
@media(prefers-reduced-motion:reduce){.task-card,.chevron,.bento-card,.bento-chip{transition:none;}}
.tj-group-hdr{display:flex;align-items:center;gap:8px;padding:8px 4px;border-bottom:1px solid #eef0f4;cursor:pointer;font-size:14px;}
.tj-items{display:flex;flex-direction:column;gap:6px;padding:6px 4px 10px;}
.tj-items label{font-size:13px;color:var(--text);display:flex;align-items:center;gap:7px;cursor:pointer;}
"""

NORMATIVA_ITEMS = [
    "REBT — Reglamento Electrotécnico para Baja Tensión (RD 842/2002) e ITC-BT aplicables. Verificar versión vigente.",
    "ITC-BT-10 / previsión de cargas; ITC-BT-25 (viviendas); ITC-BT-28 (locales pública concurrencia) según aplique.",
    "Normativa ICT vigente (RD 346/2011 y reglamento posterior) para telecomunicaciones. Verificar versión.",
    "Normas particulares de i-DE / Iberdrola para acometida, CGP y CT cuando sean de aplicación.",
    "Normas UNE aplicables al proyecto (verificar edición vigente).",
    "Normativa autonómica de Euskadi y ordenanzas municipales aplicables.",
    "Proyecto eléctrico y de telecomunicaciones de la obra e instrucciones de la Dirección Facultativa.",
    "Inspección OCA / Industria antes de la puesta en servicio cuando proceda.",
]


def _fmt_num(n):
    try:
        return f"{n:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(n)


def _e(valor):
    return html_lib.escape(str(valor if valor not in (None, '') else '—'))


def _e_atributo(valor):
    """Escapa un atributo sin sustituir por un guión los valores vacíos."""
    return html_lib.escape(str('' if valor is None else valor), quote=True)


def _ub_div(ubicacion):
    unidades = ubicacion.get('unidades') or [ubicacion.get('unidad')]
    unidades = [u for u in unidades if u not in (None, '')]
    unidades_txt = ', '.join(str(x) for x in unidades[:10]) or '—'
    if len(unidades) > 10:
        unidades_txt += f" (+{len(unidades) - 10})"
    return (f"<div style='margin-bottom:3px;'><b>{_e(ubicacion.get('edificio'))} · "
            f"planta {_e(ubicacion.get('planta'))}</b>: {_e(unidades_txt)}</div>")


def _ubicaciones_html(ubicaciones):
    if not ubicaciones:
        return '—'
    n = len(ubicaciones)
    detalle = ''.join(_ub_div(u) for u in ubicaciones)
    return (
        "<details style='margin-top:2px;'>"
        "<summary style='cursor:pointer;font-size:12px;color:var(--accent2);"
        f"white-space:nowrap;'>{n} ubicaci{'ón' if n == 1 else 'ones'}</summary>"
        f"<div style='margin-top:4px;'>{detalle}</div></details>"
    )


_GRUPOS_UBICACION_TIMELINE_VISIBLES = 6
_ESTADOS_MEDIDOS_TIMELINE = {'X', 'M'}


def _texto_timeline(valor, defecto='—'):
    """Devuelve texto no vacío para las tarjetas del orden de ejecución."""
    if valor is None or valor == '':
        return defecto
    return str(valor)


def _nombre_edificio_timeline(valor):
    """Suaviza solo nombres de edificio escritos íntegramente en mayúsculas."""
    nombre = _texto_timeline(valor)
    return nombre.title() if nombre.isupper() else nombre


def _compactar_rangos_numericos(valores):
    """Compacta una secuencia como [1, 2, 3, 7] en ``1–3, 7``."""
    numeros = sorted(set(valores))
    if not numeros:
        return ''
    tramos = []
    inicio = anterior = numeros[0]
    for numero in numeros[1:]:
        if numero == anterior + 1:
            anterior = numero
            continue
        tramos.append((inicio, anterior))
        inicio = anterior = numero
    tramos.append((inicio, anterior))
    return ', '.join(
        str(inicio) if inicio == fin else f'{inicio}–{fin}'
        for inicio, fin in tramos
    )


def _resumen_ubicaciones_timeline(ubicaciones):
    """Resume edificio, plantas y ubicaciones sin usar el agregado de estado."""
    total = len(ubicaciones)
    if not ubicaciones:
        return 'Sin ubicaciones'

    edificios = list(dict.fromkeys(
        _nombre_edificio_timeline(ub.get('edificio')) for ub in ubicaciones
    ))
    plantas_raw = list(dict.fromkeys(
        _texto_timeline(ub.get('planta')) for ub in ubicaciones
    ))
    if len(edificios) != 1:
        return (f'{len(edificios)} edificios · {len(plantas_raw)} plantas · '
                f'{total} ubicaciones')

    edificio = edificios[0]
    if all(planta.lstrip('-').isdigit() for planta in plantas_raw):
        plantas = _compactar_rangos_numericos(
            int(planta) for planta in plantas_raw)
    else:
        plantas = ', '.join(plantas_raw[:3])
        if len(plantas_raw) > 3:
            plantas += f' +{len(plantas_raw) - 3}'
    etiqueta = 'planta' if len(plantas_raw) == 1 else 'plantas'
    return f'{edificio} · {etiqueta} {plantas} · {total} ubicaciones'


def _agrupar_ubicaciones_timeline(ubicaciones):
    """Agrupa por edificio/planta conservando el orden de las ubicaciones."""
    grupos = OrderedDict()
    for ubicacion in ubicaciones:
        clave = (
            _nombre_edificio_timeline(ubicacion.get('edificio')),
            _texto_timeline(ubicacion.get('planta')),
        )
        grupos.setdefault(clave, []).append(ubicacion)
    return list(grupos.items())


def _etiqueta_unidades_timeline(ubicacion):
    """Muestra todas las unidades de una ubicación, sin el truncado del inventario."""
    unidades = ubicacion.get('unidades') or []
    if not isinstance(unidades, list):
        unidades = [unidades]
    valores = [
        _texto_timeline(unidad, '') for unidad in unidades
        if unidad not in (None, '')
    ]
    return ', '.join(valores) if valores else 'Sin unidad'


def _grupo_ubicaciones_timeline_html(clave, ubicaciones):
    edificio, planta = clave
    chips = []
    for ubicacion in ubicaciones:
        estado = _texto_timeline(
            ubicacion.get('estado_actual'), 'Sin estado')
        medido = estado in _ESTADOS_MEDIDOS_TIMELINE
        clase = 'is-done' if medido else 'is-pending'
        chips.append(
            f'<span class="location-chip {clase}" '
            f'title="Estado actual: {_e(estado)}">'
            f'<span>{_e(_etiqueta_unidades_timeline(ubicacion))}</span>'
            f'<span class="chip-state">{_e(estado)}</span></span>'
        )
    cantidad = len(ubicaciones)
    return (
        '<div class="location-group">'
        '<div class="location-group-head">'
        f'<strong>{_e(edificio)} · planta {_e(planta)}</strong>'
        f'<span>{cantidad} ubicaci{"ón" if cantidad == 1 else "ones"}</span>'
        '</div>'
        f'<div class="location-chips">{"".join(chips)}</div>'
        '</div>'
    )


def _ubicaciones_timeline_html(ubicaciones):
    """Muestra seis grupos y deja el resto accesible en un details anidado."""
    grupos = _agrupar_ubicaciones_timeline(ubicaciones)
    visibles = grupos[:_GRUPOS_UBICACION_TIMELINE_VISIBLES]
    restantes = grupos[_GRUPOS_UBICACION_TIMELINE_VISIBLES:]
    salida = [
        _grupo_ubicaciones_timeline_html(clave, grupo)
        for clave, grupo in visibles
    ]
    if restantes:
        n_restantes = sum(len(grupo) for _, grupo in restantes)
        salida.append(
            '<details class="more-locations">'
            f'<summary>+{n_restantes} ubicaciones más en {len(restantes)} '
            f'planta{"s" if len(restantes) != 1 else ""}</summary>'
            '<div class="more-locations-content">'
            + ''.join(
                _grupo_ubicaciones_timeline_html(clave, grupo)
                for clave, grupo in restantes
            )
            + '</div></details>'
        )
    return ''.join(salida) if salida else '<p class="empty">Sin ubicaciones.</p>'


def _contar_avance_timeline(ubicaciones):
    """Cuenta X/M como medido y cualquier otro estado como pendiente."""
    medidos = sum(
        1 for ubicacion in ubicaciones
        if ubicacion.get('estado_actual') in _ESTADOS_MEDIDOS_TIMELINE
    )
    total = len(ubicaciones)
    pendientes = total - medidos
    porcentaje = round((medidos / total) * 100) if total else 0
    return medidos, pendientes, total, porcentaje


def _tarjeta_timeline_html(item):
    """Pinta un tajo como nodo numerado y tarjeta nativa desplegable."""
    ubicaciones = item.get('ubicaciones') or []
    medidos, pendientes, total, porcentaje = _contar_avance_timeline(
        ubicaciones)
    situacion = _texto_timeline(item.get('situacion'))
    clase_estado = 'ok' if situacion == 'LISTO' else 'warn'
    icono_estado = ('' if situacion == 'LISTO'
                    else '<span aria-hidden="true">⚠ </span>')
    orden = item.get('orden')
    identificador = 'tajo-' + ''.join(
        caracter if caracter.isalnum() else '-'
        for caracter in _texto_timeline(
            item.get('tarea_id'), str(orden)).lower()
    )
    motivo = _texto_timeline(item.get('motivo'))
    impacto = _texto_timeline(item.get('impacto_gremios'), '')
    impacto_html = ''
    if impacto and impacto != motivo:
        impacto_html = (
            '<div class="reason-block secondary-reason">'
            '<p class="detail-label">IMPACTO EN GREMIOS</p>'
            f'<p>{_e(impacto)}</p></div>'
        )

    return f"""
      <article class="timeline-item" data-sit="{_e_atributo(situacion)}" data-fase="{_e_atributo(item.get('fase_nombre'))}" data-order="{_e_atributo(orden)}">
        <div class="timeline-node {clase_estado}" aria-hidden="true">{_e(orden)}</div>
        <details class="task-card {clase_estado}" id="{_e_atributo(identificador)}" data-total="{total}" data-reported-total="{_e_atributo(item.get('n_ubicaciones'))}">
          <summary>
            <span class="summary-topline">
              <span class="badge {clase_estado}">{icono_estado}{_e(situacion)}</span>
              <span class="task-meta">Orden lógico {_e(item.get('orden_ejecucion'))} · {_e(item.get('fase_nombre'))} · {_e(item.get('ambito_nombre'))}</span>
            </span>
            <span class="summary-titleline">
              <span class="task-title" role="heading" aria-level="3">{_e(item.get('trabajo'))}</span>
              <span class="scope">{_e(item.get('n_unidades'))} ud. · {total} ubicaciones</span>
            </span>
            <span class="compact-bottom">
              <span class="progress-wrap">
                <span class="progress-track" role="progressbar" aria-label="Ubicaciones medidas" aria-valuemin="0" aria-valuemax="{total}" aria-valuenow="{medidos}">
                  <span class="progress-fill" style="width:{porcentaje}%"></span>
                </span>
                <span class="progress-copy">{porcentaje}% · {medidos} medidos · {pendientes} pendientes</span>
              </span>
              <span class="location-summary"><span aria-hidden="true">⌖</span> {_e(_resumen_ubicaciones_timeline(ubicaciones))}</span>
            </span>
            <span class="chevron" aria-hidden="true"></span>
          </summary>
          <div class="task-detail">
            <div class="stat-grid" aria-label="Resumen de ubicaciones">
              <div class="stat done"><strong>{medidos}</strong><span>Medidos</span></div>
              <div class="stat pending"><strong>{pendientes}</strong><span>Pendientes</span></div>
              <div class="stat total"><strong>{total}</strong><span>Total</span></div>
            </div>
            <div class="locations-block">
              <div class="detail-heading">
                <p class="detail-label">UBICACIONES ({total})</p>
                <p class="location-legend"><span class="legend-dot done"></span>X/M medido <span class="legend-dot pending"></span>Resto pendiente</p>
              </div>
              {_ubicaciones_timeline_html(ubicaciones)}
            </div>
            <div class="reason-block">
              <p class="detail-label">MOTIVO / COMPROBAR</p>
              <p>{_e(motivo)}</p>
            </div>
            {impacto_html}
            <p class="technical-meta">Categoría: {_e(item.get('categoria'))} · Prioridad: {_e(item.get('prioridad'))} · Celdas en hoja: {_e(item.get('n_celdas'))}</p>
          </div>
        </details>
      </article>"""


def _envolver_plegable(id_ancla, titulo_html, contenido_html, color_borde=None):
    """Envuelve una seccion de Prioridades en un <details> plegable.

    Mismo widget nativo que el panel ya usa para 'Mostrar tajos terminados'
    y 'Ver ubicaciones afectadas'. Sin librerias de acordeon.
    """
    estilo = f" style='border-left:4px solid {color_borde};'" if color_borde else ''
    return (
        f"<details class='card seccion-plegable' id='{_e_atributo(id_ancla)}'{estilo}>"
        f"<summary>{titulo_html}</summary>"
        f"<div class='seccion-contenido'>{contenido_html}</div>"
        "</details>"
    )


_SCRIPT_INDICE_PRIORIDADES = """
<script>
function _iniciarNavPrioridades() {
  document.querySelectorAll('.indice-nav-link').forEach(function(enlace) {
    enlace.addEventListener('click', function(ev) {
      var destino = document.getElementById(enlace.getAttribute('data-abre'));
      if (destino) {
        ev.preventDefault();
        destino.style.display = 'block';
        destino.open = true;
        destino.scrollIntoView({behavior: 'smooth', block: 'start'});
      }
      var menu = enlace.closest('details.indice-nav-grupo');
      if (menu) { menu.open = false; }
    });
  });
  [
    'sec-tareas', 'sec-dudas', 'sec-ejecucion', 'sec-inv-bloqueado',
    'sec-inv-sin_revisar', 'sec-inv-viable', 'sec-inv-otros_gremios',
    'sec-inv-dudas', 'sec-inv-terminado', 'sec-preguntas-catalogo',
    'sec-prevision'
  ].forEach(function(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('toggle', function() {
      if (!el.open) { el.style.display = 'none'; }
    });
  });
}
// El script se inserta antes que las secciones a las que apunta (viven mas
// abajo en el HTML), asi que getElementById no las encuentra si se ejecuta
// en el momento en que el parser llega aqui. DOMContentLoaded garantiza que
// todo el documento ya existe, sin depender del orden de impresion.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _iniciarNavPrioridades);
} else {
  _iniciarNavPrioridades();
}
</script>
"""


def _indice_prioridades(secciones):
    """secciones: lista de dicts {id, etiqueta, grupo, color opcional}, en
    el orden en que deben salir dentro de su grupo. 'grupo' es 'actuar' o
    'consulta'. Un apartado que no se pasa aqui simplemente no aparece: el
    indice nunca declara algo que la pagina no vaya a pintar.

    Se pinta como una barra de navegacion (mismo azul de la cabecera del
    panel) con un desplegable por grupo, en vez de una lista larga de
    tarjetas: mezclada con las secciones reales (tambien tarjetas), la
    lista se leia como "mas contenido" en vez de como un menu."""
    if not secciones:
        return ''

    def _desplegable(etiqueta_boton, codigo_grupo):
        items = [s for s in secciones if s['grupo'] == codigo_grupo]
        if not items:
            return ''
        enlaces = ''.join(
            f"<a class='indice-nav-link' href='#{_e_atributo(s['id'])}' "
            f"data-abre='{_e_atributo(s['id'])}' "
            f"style='border-left:3px solid {s.get('color') or 'var(--muted)'};'>"
            f"<span>{_e(s['etiqueta'])}</span></a>"
            for s in items
        )
        return (
            "<details class='indice-nav-grupo' name='indice-nav-grupo'>"
            f"<summary>{_e(etiqueta_boton)}</summary>"
            f"<div class='indice-nav-panel'>{enlaces}</div></details>"
        )

    return ("<nav class='indice-nav'>"
            "<span class='indice-nav-label'>Ir a</span>"
            + _desplegable('Para actuar hoy', 'actuar')
            + _desplegable('Consulta y referencia', 'consulta')
            + "</nav>" + _SCRIPT_INDICE_PRIORIDADES)


_DUDA_ETIQUETAS = {
    "NO_QUITAR_X":          "Revisar en obra",
    "TAJO_NUEVO":           "Tajo no reconocido",
    "OMITIDO_SIN_X":        "Desapareció sin terminar",
    "ALCANCE_POSTAPERTURA": "Alcance por confirmar",
    "ESTADOS_DUPLICADOS":   "Estado duplicado en hoja",
}

_ORDEN_ETIQUETAS = {
    "ORDEN_SIN_CONFIRMAR":          "Sin posición en la secuencia",
    "TAJO_FUERA_DEL_CATALOGO":      "No está en el catálogo",
    "TAJO_DUPLICADO_EN_LA_BASE":    "Dos filas para el mismo tajo",
    "DEPENDENCIA_AUSENTE_EN_LA_OBRA": "Depende de un tajo que la obra no tiene",
}

_ID_SEC_PREGUNTAS_CATALOGO = 'sec-preguntas-catalogo'
_ID_SEC_PREVISION = 'sec-prevision'
_ID_SEC_DUDAS = 'sec-dudas'

_SECCIONES_INVENTARIO = [
    ('VIABLE', 'Tajos viables',
     'Se pueden ejecutar según los datos disponibles.'),
    ('BLOQUEADO', 'Tajos bloqueados',
     'Son propios, pero falta una dependencia previa.'),
    ('OTROS_GREMIOS', 'Otros gremios e interferencias',
     'Se controlan solo para saber cuándo puede entrar electricidad.'),
    ('DUDAS', 'Sin clasificar o por verificar',
     'No se decide ni se fusiona hasta recibir confirmación.'),
    ('SIN_REVISAR', 'Sin revisar nunca',
     'Nadie los ha mirado todavía. No son trabajo pendiente: son trabajo '
     'por comprobar.'),
    ('TERMINADO', 'Tajos terminados',
     'Histórico conservado; siempre se muestra al final.'),
]


def _tabla_preguntas_orden(preguntas):
    """Lo que el catalogo no sabe resolver solo. Es la puerta por la que el
    catalogo crece: cada fila es una decision que hay que tomar."""
    if not preguntas:
        return ''
    filas = ''
    for p in preguntas:
        etiqueta = _ORDEN_ETIQUETAS.get(p.get('codigo'), p.get('codigo', ''))
        parecidos = p.get('parecidos') or []
        pista = ''
        if parecidos:
            pista = (f"<div style='font-size:11.5px;color:var(--muted);"
                     f"margin-top:3px;'>Candidatos: {_e(', '.join(parecidos))}</div>")
        filas += (f"<tr><td style='white-space:nowrap;'><b>{_e(etiqueta)}</b></td>"
                  f"<td><b>{_e(p.get('nombre'))}</b>"
                  f"<div style='font-size:11px;color:var(--muted);'>"
                  f"{_e(p.get('tarea_id'))}</div>{pista}</td></tr>")
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "El catálogo manda sobre el orden y las dependencias, y es "
        "siempre ampliable. Estas son las decisiones que faltan para que "
        "estos tajos ocupen su sitio en la secuencia.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Qué pasa</th><th>Tajo</th></tr></thead><tbody>"
        + filas + "</tbody></table></div>")
    return _envolver_plegable(
        _ID_SEC_PREGUNTAS_CATALOGO, 'Preguntas sobre el catálogo de tajos',
        contenido, color_borde='var(--warn)')


def _tabla_prevision(prevision):
    """Que se libera al terminar cada tajo, de mayor a menor."""
    if not prevision:
        return ''
    filas = ''
    for p in prevision[:25]:
        propio = p.get('propiedad') == 'propio'
        badge = ("<span class='badge ok'>Nuestro</span>" if propio
                 else "<span class='badge'>Otro gremio</span>")
        filas += (f"<tr><td><b>{_e(p.get('trabajo'))}</b> {badge}</td>"
                  f"<td style='font-size:12px;'>{_e(p.get('estado_actual'))}</td>"
                  f"<td style='text-align:right;'><b>{_e(p.get('desbloquea'))}</b></td>"
                  f"<td style='font-size:12px;'>"
                  f"{_e(', '.join(p.get('tajos_afectados') or []))}</td></tr>")
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ordenado por lo que más libera. Una obra dura meses: saber qué "
        "abre paso a qué es lo que permite llevar el orden hasta el "
        "final.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Al terminar</th><th>Ahora está</th><th style='text-align:right;'>"
        "Libera</th><th>Deja pasar a</th>"
        "</tr></thead><tbody>" + filas + "</tbody></table></div>")
    return _envolver_plegable(
        _ID_SEC_PREVISION, 'Qué se desbloquea al terminar cada cosa', contenido)


def _campo_riesgo(registro, *nombres):
    """Lee una columna manual aunque la plantilla use su nombre corto."""
    por_nombre = {
        str(k).strip().casefold(): v
        for k, v in (registro or {}).items()
    }
    for nombre in nombres:
        valor = por_nombre.get(nombre.casefold())
        if valor not in (None, ''):
            return valor
    return ''


def _tabla_riesgos_manuales(riesgos):
    if not riesgos:
        return ''
    filas = ''
    for riesgo in riesgos:
        valores = [
            _campo_riesgo(riesgo, 'Riesgo'),
            _campo_riesgo(riesgo, 'Tipo'),
            _campo_riesgo(riesgo, 'Probabilidad', 'Prob.'),
            _campo_riesgo(riesgo, 'Impacto'),
            _campo_riesgo(riesgo, 'Acción preventiva', 'Acción'),
            _campo_riesgo(riesgo, 'Fecha límite'),
            _campo_riesgo(riesgo, 'Estado'),
        ]
        filas += '<tr>' + ''.join(f'<td>{_e(v)}</td>' for v in valores) + '</tr>'
    return (
        "<div class='card'><h3>Registro manual</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Riesgos declarados en <b>FICHA DE OBRA.xlsx</b>. Probabilidad, "
        "impacto y fecha solo se muestran cuando alguien los ha registrado; "
        "el sistema no los inventa.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Riesgo</th><th>Tipo</th><th>Probabilidad declarada</th>"
        "<th>Impacto declarado</th><th>Acción</th><th>Fecha límite</th>"
        "<th>Estado</th></tr></thead><tbody>" + filas
        + "</tbody></table></div></div>"
    )


def _tabla_bloqueos_riesgo(prevision):
    if not prevision:
        return (
            "<div class='card'><h3>Bloqueos activos que frenan trabajo Sagarde</h3>"
            "<p class='empty'>La base y el catálogo no producen dependencias "
            "bloqueantes en esta actualización.</p></div>"
        )

    etiquetas = {
        'propio': ('Sagarde', 'ok'),
        'externo': ('Otro gremio', 'warn'),
        'coordinacion': ('Coordinación', 'warn'),
    }
    acciones = {
        'propio': 'Priorizar dentro de Sagarde por su efecto desbloqueante.',
        'externo': 'Coordinar su cierre y confirmarlo en la siguiente revisión.',
        'coordinacion': 'Cerrar la decisión o coordinación antes de liberar el frente.',
    }
    filas = ''
    for item in prevision[:25]:
        propiedad = item.get('propiedad') or 'desconocido'
        etiqueta, clase = etiquetas.get(propiedad, ('Por confirmar', 'bad'))
        afectados = ', '.join(item.get('tajos_afectados') or []) or '—'
        accion = acciones.get(
            propiedad, 'Confirmar responsable y condición de desbloqueo.')
        filas += (
            '<tr>'
            f"<td><b>{_e(item.get('trabajo'))}</b></td>"
            f"<td><span class='badge {clase}'>{_e(etiqueta)}</span></td>"
            f"<td>{_e(item.get('estado_actual'))}</td>"
            f"<td style='text-align:right;'><b>{_e(item.get('desbloquea'))}</b></td>"
            f"<td>{_e(afectados)}</td><td>{_e(accion)}</td>"
            '</tr>'
        )
    return (
        "<div class='card'><h3>Bloqueos activos que frenan trabajo Sagarde</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ordenados por lo que más liberan. La magnitud cuenta unidades "
        "reales según el ámbito del tajo, no simples celdas.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Condicionante</th><th>Origen</th><th>Estado actual</th>"
        "<th style='text-align:right;'>Libera</th><th>Tajos Sagarde afectados</th>"
        "<th>Acción operativa</th></tr></thead><tbody>" + filas
        + "</tbody></table></div></div>"
    )


def _tabla_controles_riesgo(prioridades, bloqueos, sin_cambios):
    resumen = prioridades.get('resumen') or {}
    revision = prioridades.get('revision') or '—'
    sin_revisar = resumen.get('unidades_sin_revisar', 0)
    preguntas = resumen.get('preguntas_pendientes', 0)
    controles = []

    if prioridades.get('revision_caducada'):
        edad = prioridades.get('edad_revision_dias')
        evidencia = f"Revisión {revision}"
        if edad is not None:
            evidencia += f" · {edad} días"
        controles.append((
            'Revisión desactualizada', evidencia,
            'Actualizar la revisión de campo antes de decidir nuevos frentes.',
            'Verificar'))
    if sin_revisar:
        controles.append((
            'Cobertura pendiente', f'{sin_revisar} unidades sin revisar nunca',
            'Comprobarlas en campo; desconocido no equivale a pendiente.',
            'Verificar'))
    if preguntas:
        controles.append((
            'Decisiones sin resolver', f'{preguntas} decisiones pendientes',
            'Resolver alcance, duplicados o dependencias en la base/catálogo.',
            'Verificar'))
    if sin_cambios:
        controles.append((
            'Dos revisiones idénticas',
            'Las dos últimas revisiones no cambian ninguna celda',
            'Confirmar que la hoja de campo fue realmente actualizada.',
            'Verificar'))
    for bloqueo in bloqueos[:20]:
        controles.append((
            'Desviación de avance', bloqueo.get('motivo') or '—',
            'Verificar en obra la causa de la diferencia respecto a su entorno.',
            'Seguimiento'))

    if not controles:
        return (
            "<div class='card'><h3>Calidad del dato y desviaciones de avance</h3>"
            "<p class='empty'>Sin señales automáticas de control en esta actualización.</p>"
            "</div>"
        )

    filas = ''.join(
        '<tr>'
        f'<td><b>{_e(senal)}</b></td><td>{_e(evidencia)}</td>'
        f'<td>{_e(accion)}</td><td><span class="badge warn">{_e(estado)}</span></td>'
        '</tr>'
        for senal, evidencia, accion, estado in controles
    )
    return (
        "<div class='card'><h3>Calidad del dato y desviaciones de avance</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Estas señales no demuestran por sí solas un bloqueo de producción; "
        "indican qué conviene verificar.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Señal</th><th>Evidencia</th><th>Acción</th><th>Estado</th>"
        "</tr></thead><tbody>" + filas + "</tbody></table></div></div>"
    )


def bloque_riesgos(prioridades, bloqueos=None, riesgos_manual=None,
                    sin_cambios=False):
    """Reconstruye Riesgos con los datos calculados en el ciclo actual.

    Las prioridades ya proceden de ficha_obra.json y del catálogo. Los
    bloqueos de dependencias son hechos materializados, no riesgos
    probabilísticos, y se muestran con la magnitud real que desbloquean.
    """
    prioridades = prioridades or {}
    bloqueos = bloqueos or []
    riesgos_manual = riesgos_manual or []
    manual_html = _tabla_riesgos_manuales(riesgos_manual)

    if prioridades.get('sin_base'):
        avisos = prioridades.get('avisos') or [
            'Esta obra no tiene base de datos todavía.']
        return (
            "<div class='banner bad'><b>Riesgos no evaluables:</b> "
            + _e(avisos[0])
            + " El panel no publica un cero ni afirma que no haya riesgos."
              "</div>" + manual_html
        )

    resumen = prioridades.get('resumen') or {}
    prevision = prioridades.get('prevision') or []
    revision = prioridades.get('revision') or '—'
    bloqueados = resumen.get('bloqueados', 0)
    sin_revisar = resumen.get('unidades_sin_revisar', 0)
    preguntas = resumen.get('preguntas_pendientes', 0)

    cabecera = (
        "<div class='card'><h3>Riesgos de producción Sagarde</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:12px;'>"
        "Se recalculan al actualizar SAGARDE desde la base viva de la obra, "
        "el catálogo de dependencias y la revisión <b>" + _e(revision)
        + "</b>. Un bloqueo activo se presenta como hecho; no se le asigna "
          "una probabilidad ficticia.</p>"
        "<div class='kpi-row' style='margin-bottom:0;'>"
        "<div class='kpi'><div class='label'>Tajos bloqueados</div>"
        f"<div class='value'>{_e(bloqueados)}</div>"
        "<div class='hint'>Familias de trabajo Sagarde</div></div>"
        "<div class='kpi'><div class='label'>Condicionantes activos</div>"
        f"<div class='value'>{_e(len(prevision))}</div>"
        "<div class='hint'>Dependencias que frenan producción</div></div>"
        "<div class='kpi'><div class='label'>Sin revisar</div>"
        f"<div class='value'>{_e(sin_revisar)}</div>"
        "<div class='hint'>Unidades de dato por comprobar</div></div>"
        "<div class='kpi'><div class='label'>Decisiones pendientes</div>"
        f"<div class='value'>{_e(preguntas)}</div>"
        "<div class='hint'>Alcance, catálogo u orden</div></div>"
        "</div></div>"
    )
    return (
        cabecera
        + _tabla_bloqueos_riesgo(prevision)
        + _tabla_controles_riesgo(prioridades, bloqueos, sin_cambios)
        + manual_html
    )


def bloque_cierre(cierre, avisos=None):
    """HTML de la pestana Cierre de expediente.

    `cierre` es la forma que devuelve cierre_expediente.cargar()/vacio():
    {"obra":..., "actualizado":..., "hitos": {id: {"estado","fecha","nota"}}}.
    Dato de obra editado a mano, al margen de la rejilla de revisiones.
    """
    import cierre_expediente as ce
    cierre = cierre or ce.vacio()
    avisos = avisos or []

    avisos_html = ""
    if avisos:
        avisos_html = "".join(
            f"<div class='banner bad'>⚠ {_e(a)}</div>" for a in avisos)

    filas = ""
    for hito_id in ce.HITOS_ORDEN:
        datos_hito = (cierre.get('hitos') or {}).get(hito_id) or {
            'estado': 'pendiente', 'fecha': None, 'nota': ''}
        nombre = ce.HITOS_NOMBRE.get(hito_id, hito_id)
        estado = datos_hito.get('estado') or 'pendiente'
        badge = 'ok' if estado in ('hecho', 'favorable') else (
            'bad' if estado in ('condicionada', 'negativa') else 'warn')
        fecha = datos_hito.get('fecha') or '—'
        nota = datos_hito.get('nota') or '—'
        filas += (
            f"<tr><td>{_e(nombre)}</td>"
            f"<td><span class='badge {badge}'>{_e(estado)}</span></td>"
            f"<td>{_e(fecha)}</td><td>{_e(nota)}</td></tr>"
        )

    actualizado = cierre.get('actualizado') or 'sin actualizar todavía'
    return (
        avisos_html
        + "<div class='card'><h3>Cierre de expediente</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ensayos, inspección OCA, CIE/Boletín y Libro del Edificio. Dato de "
        "obra editado a mano, no calculado desde las revisiones de campo. "
        f"Última actualización: {_e(actualizado)}.</p>"
        "<table class='data'><thead><tr><th>Hito</th><th>Estado</th>"
        "<th>Fecha</th><th>Nota</th></tr></thead>"
        f"<tbody>{filas}</tbody></table></div>"
    )


_ID_SEC_TAREAS = 'sec-tareas'


def _tarea_hecha(tarea):
    return str(tarea.get('Estado') or '').strip().casefold() == 'hecho'


def _tarea_pendiente(tarea):
    return str(tarea.get('Estado') or '').strip().casefold() == 'pendiente'


def _tarea_clave_fecha(tarea):
    texto = str(tarea.get('Fecha') or '').strip()
    try:
        return (0, datetime.strptime(texto, '%d/%m/%Y'))
    except ValueError:
        # Una fecha vacía o no normalizada no debe romper el panel. Se
        # conserva al final de las pendientes, ordenada por su texto.
        return (1, texto.casefold())


def _tareas_pendientes(tareas):
    """Las tareas no hechas, ordenadas por fecha. La usan tanto la tarjeta
    de Tareas manuales como el indice, para que el numero de una y otro
    salgan siempre del mismo calculo — nunca de dos formulas parecidas."""
    return sorted(
        (tarea for tarea in (tareas or []) if not _tarea_hecha(tarea)),
        key=_tarea_clave_fecha)


_SCRIPT_MARCAR_TAREA = """<script>
document.querySelectorAll('.marcar-tarea-hecha').forEach(casilla => {
  casilla.addEventListener('change', async () => {
    const objetivo = casilla.checked ? 'Hecho' : 'Pendiente';
    casilla.disabled = true;
    const fila = casilla.closest('tr');
    const tarjeta = casilla.closest('.card');
    const mensaje = tarjeta.querySelector('.tarea-resultado');
    const contador = tarjeta.querySelector('.tareas-pendientes-contador');
    const controlador = new AbortController();
    const timeout = setTimeout(() => controlador.abort(), 3000);
    const restaurar = () => {
      casilla.checked = !casilla.checked;
      casilla.disabled = false;
    };
    const avisar = (texto, error) => {
      mensaje.textContent = texto;
      mensaje.style.color = error ? 'var(--bad)' : 'var(--ok)';
      mensaje.style.display = 'block';
    };
    try {
      const respuesta = await fetch('/api/marcar_hecho', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          obra_carpeta: casilla.dataset.obra,
          tarea: casilla.dataset.tarea,
          origen: casilla.dataset.origen,
          fecha: casilla.dataset.fecha,
          archivo: casilla.dataset.archivo,
          objetivo: objetivo
        }),
        signal: controlador.signal
      });
      if (respuesta.ok) {
        const marcandoHecha = objetivo === 'Hecho';
        fila.style.color = marcandoHecha ? 'var(--muted)' : '';
        fila.style.textDecoration = marcandoHecha ? 'line-through' : '';
        const estado = fila.querySelector('.badge');
        estado.textContent = objetivo;
        estado.classList.toggle('f3', marcandoHecha);
        estado.classList.toggle('warn', !marcandoHecha);
        const delta = marcandoHecha ? -1 : 1;
        const restantes = Math.max(
          0, parseInt(contador.dataset.pendientes, 10) + delta);
        contador.dataset.pendientes = restantes;
        contador.textContent = restantes + ' '
          + (restantes === 1 ? 'pendiente' : 'pendientes');
        avisar(marcandoHecha
          ? 'Marcada como hecha. Recuerda ejecutar Actualizar_Sagarde.bat para publicar este cambio.'
          : 'Marcada de nuevo como pendiente. Recuerda ejecutar Actualizar_Sagarde.bat para publicar este cambio.',
          false);
        casilla.disabled = false;
      } else if (respuesta.status === 404) {
        restaurar();
        avisar('No se encontró esa tarea en el Excel; puede que el panel '
          + 'esté desactualizado. Regenera antes de reintentar.', true);
      } else {
        restaurar();
        avisar('No se pudo guardar: esto solo funciona abriendo el panel en '
          + 'local con Abrir_Panel_Local.bat. No se ha guardado ningún cambio.',
          true);
      }
    } catch (error) {
      restaurar();
      avisar('No se pudo guardar: esto solo funciona abriendo el panel en '
        + 'local con Abrir_Panel_Local.bat. No se ha guardado ningún cambio.',
        true);
    } finally {
      clearTimeout(timeout);
    }
  });
});
</script>"""


def _tabla_tareas_manuales(tareas, documentos, obra=''):
    """Pinta las tareas de la ficha y enlaza su documento cuando existe."""
    tareas = tareas or []
    if not tareas:
        return ''

    href_por_nombre = {}
    for documento in documentos or []:
        nombre = str(documento.get('nombre') or '').strip()
        href = documento.get('href')
        if nombre and href not in (None, ''):
            href_por_nombre.setdefault(nombre.casefold(), str(href))

    pendientes = _tareas_pendientes(tareas)
    hechas = [tarea for tarea in tareas if _tarea_hecha(tarea)]

    def archivo_html(tarea):
        archivo = str(tarea.get('Archivo') or '').strip()
        if not archivo:
            return _e(None)
        href = href_por_nombre.get(archivo.casefold())
        if href is None:
            return _e(archivo)
        return f'<a href="{_e(href)}">{_e(archivo)}</a>'

    def fila(tarea, hecha=False):
        estado = tarea.get('Estado') or 'Sin estado'
        estilo = (" style='color:var(--muted);text-decoration:line-through;'"
                  if hecha else '')
        clase = 'f3' if hecha else 'warn'
        # Solo se ofrece la casilla cuando el estado actual es exactamente
        # Pendiente o Hecho: un valor ambiguo no dice en qué sentido cambiar,
        # y no se adivina.
        if hecha or _tarea_pendiente(tarea):
            casilla = (
                "<td><label style='white-space:nowrap;cursor:pointer;'>"
                "<input type='checkbox' class='marcar-tarea-hecha'"
                + (' checked' if hecha else '')
                + f" data-obra='{_e_atributo(obra)}'"
                f" data-tarea='{_e_atributo(tarea.get('Tarea'))}'"
                f" data-origen='{_e_atributo(tarea.get('Origen'))}'"
                f" data-fecha='{_e_atributo(tarea.get('Fecha'))}'"
                f" data-archivo='{_e_atributo(tarea.get('Archivo'))}'> Hecho"
                "</label></td>"
            )
        else:
            casilla = '<td></td>'
        return (
            f"<tr{estilo}><td><span class='badge {clase}'>{_e(estado)}</span></td>"
            f"<td><b>{_e(tarea.get('Tarea'))}</b></td>"
            f"<td>{_e(tarea.get('Origen'))}</td>"
            f"<td style='white-space:nowrap;'>{_e(tarea.get('Fecha'))}</td>"
            f"<td>{archivo_html(tarea)}</td>{casilla}</tr>"
        )

    filas_pendientes = ''.join(fila(tarea) for tarea in pendientes)
    if filas_pendientes:
        bloque_pendientes = (
            "<div class='tareas-pendientes'><div class='table-scroll'>"
            "<table class='data'><thead><tr><th>Estado</th><th>Tarea</th>"
            "<th>Origen</th><th>Fecha</th><th>Archivo</th><th>Acción</th>"
            "</tr></thead>"
            f"<tbody>{filas_pendientes}</tbody></table></div></div>"
        )
    else:
        bloque_pendientes = '<p class="empty">Sin tareas pendientes.</p>'

    bloque_hechas = ''
    if hechas:
        filas_hechas = ''.join(fila(tarea, hecha=True) for tarea in hechas)
        bloque_hechas = (
            "<div class='tareas-hechas' "
            "style='margin-top:16px;color:var(--muted);'>"
            "<h4 style='font-size:12px;margin-bottom:6px;'>Hechas</h4>"
            "<div class='table-scroll'><table class='data'><tbody>"
            f"{filas_hechas}</tbody></table></div></div>"
        )

    n_pendientes = len(pendientes)
    etiqueta = 'pendiente' if n_pendientes == 1 else 'pendientes'
    titulo = (
        "Tareas manuales "
        f"<span class='badge tareas-pendientes-contador' "
        f"data-pendientes='{n_pendientes}'>{n_pendientes} {etiqueta}</span>"
    )
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Acciones declaradas en la hoja <b>Tareas</b> de "
        "<b>FICHA DE OBRA.xlsx</b>. Se muestran aparte: no modifican los "
        "KPI ni el orden calculado de los tajos.</p>"
        f"{bloque_pendientes}{bloque_hechas}"
        "<p class='tarea-resultado' role='status' "
        "style='display:none;font-size:12.5px;margin-top:10px;'></p>"
    )
    tarjeta = _envolver_plegable(
        _ID_SEC_TAREAS, titulo, contenido, color_borde='var(--accent2)')
    hay_casillas = bool(hechas) or any(
        _tarea_pendiente(tarea) for tarea in pendientes)
    return tarjeta + (_SCRIPT_MARCAR_TAREA if hay_casillas else '')


_ID_SEC_EJECUCION = 'sec-ejecucion'


def bloque_prioridades_partes(prioridades, tareas_manual=None,
                              documentos=None, obra='', avance_pct=None):
    """Calcula las piezas de Prioridades por separado, sin concatenarlas.

    Usada por bloque_prioridades() (reconstruye el HTML de siempre) y por
    el informe de obra a la carta (usa solo las piezas marcadas). El
    cálculo vive aquí una sola vez: ninguna cifra se recalcula por un
    camino distinto para el selector.
    """
    prioridades = prioridades or {}
    if prioridades.get('sin_base'):
        avisos = prioridades.get('avisos') or [
            'Esta obra no tiene base de datos todavía.']
        return ("<div class='banner bad'>⚠ " + _e(avisos[0]) + "</div>"
                "<p style='font-size:12.5px;color:var(--muted);'>Las "
                "prioridades salen de la base de datos de la obra. Sin ella "
                "no se calcula nada: un recuento vacío sería un dato falso."
                "</p>")

    e = _e
    tareas_manual_html = _tabla_tareas_manuales(
        tareas_manual, documentos, obra=obra)
    resumen_prio = prioridades.get('resumen', {})
    items_prio = prioridades.get('items', [])
    inventario_prio = prioridades.get('inventario', [])
    dudas_prio = prioridades.get('dudas_pendientes', [])
    n_tareas_pendientes = len(_tareas_pendientes(tareas_manual))
    # Contados sobre los tajos reales de items_prio, no sobre resumen_prio:
    # el resumen es un calculo aparte del priorizador y puede desincronizarse
    # de lo que el timeline realmente pinta (bug real detectado en revision,
    # invisible mientras VERIFICAR fue siempre 0 en obras reales).
    n_listos_real = sum(
        1 for item in items_prio if item.get('situacion') == 'LISTO')
    n_verificar_real = sum(
        1 for item in items_prio if item.get('situacion') == 'VERIFICAR')

    tarjetas_prio = ''.join(
        _tarjeta_timeline_html(item) for item in items_prio)
    if not tarjetas_prio:
        tarjetas_prio = (
            '<p class="empty">No se han identificado bloques ejecutables '
            'con las reglas y datos actuales.</p>')

    _bp = ("El inventario incluye", "Los nombres nuevos", "Una X histórica",
           "El orden sigue")
    avisos_prio = ''.join(
        f'<div class="banner{" bad" if any(k in aviso.lower() for k in ("fusionan", "rejilla", "error")) else ""}">⚠ {e(aviso)}</div>'
        for aviso in prioridades.get('avisos', [])
        if not any(aviso.startswith(bp) for bp in _bp)
    )

    estado_obra_html = ''
    if prioridades.get('estado_obra'):
        estado_obra_html = f'<div class="banner">ℹ <b>Estado de la obra:</b> {e(prioridades.get("estado_obra"))}</div>'

    if dudas_prio:
        filas_dudas = ''
        for duda in dudas_prio:
            codigo = duda.get('codigo', '')
            etiqueta = _DUDA_ETIQUETAS.get(codigo, codigo)
            pregunta = duda.get('pregunta', '')
            n_ub = duda.get('n_ubicaciones', 0)
            por_planta = {}
            for ub in duda.get('ubicaciones', []):
                p = ub.get('planta', '?')
                u = ub.get('unidad', '?')
                por_planta.setdefault(p, []).append(u)

            def _sort_key(p):
                texto = str(p).strip()
                if texto.isdigit():
                    return (1, int(texto), '')
                if texto.casefold() in {'pb', 'b', 'bajo', 'baja', 'planta baja'}:
                    return (0, 0, '')
                return (2, 0, texto)
            ub_filas = ''.join(
                f"<tr><td style='padding:2px 8px;'>Planta {e(p)}</td>"
                f"<td style='padding:2px 8px;'>{e(', '.join(por_planta[p]))}</td></tr>"
                for p in sorted(por_planta, key=_sort_key)
            )
            ub_detail = (
                f"<details style='margin-top:6px;'>"
                f"<summary style='cursor:pointer;font-size:12px;color:var(--accent);'>"
                f"Ver {n_ub} ubicaciones afectadas</summary>"
                f"<div style='margin-top:4px;overflow-x:auto;'>"
                f"<table style='border-collapse:collapse;font-size:12px;'>"
                f"<thead><tr><th style='padding:2px 8px;text-align:left;'>Planta</th>"
                f"<th style='padding:2px 8px;text-align:left;'>Unidades</th></tr></thead>"
                f"<tbody>{ub_filas}</tbody></table></div></details>"
            ) if por_planta else ''
            filas_dudas += (
                f"<tr><td style='white-space:nowrap;'><b>{e(etiqueta)}</b></td>"
                f"<td>{e(pregunta)}{ub_detail}</td>"
                f"<td style='text-align:center;'>{n_ub}</td></tr>"
            )
        contenido_dudas = (
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "Resolver estas dudas antes de planificar los tajos afectados. "
            "Pincha en cada fila para ver las plantas y unidades concretas.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Tipo</th><th>Qué hay que comprobar</th><th>Uds.</th>"
            "</tr></thead><tbody>"
            + filas_dudas + "</tbody></table></div>")
        dudas_html = _envolver_plegable(
            _ID_SEC_DUDAS, 'Preguntas pendientes antes de decidir',
            contenido_dudas, color_borde='var(--warn)')
    else:
        contenido_dudas = (
            '<p style="color:var(--ok);font-size:13px;">✓ No hay preguntas '
            'pendientes en esta actualización.</p>')
        dudas_html = _envolver_plegable(
            _ID_SEC_DUDAS, 'Preguntas pendientes antes de decidir', contenido_dudas)

    orden_html = _tabla_preguntas_orden(prioridades.get('preguntas_orden'))
    prevision_html = _tabla_prevision(prioridades.get('prevision'))

    inventario_por_codigo = {}
    for codigo, titulo, explicacion in _SECCIONES_INVENTARIO:
        grupos = [g for g in inventario_prio if g.get('seccion') == codigo]
        filas = ''
        for g in grupos:
            subtajos = g.get('subtajos', [])
            sub_txt = ''
            if len(subtajos) > 1:
                sub_txt = f"<div style='font-size:11px;color:var(--muted);'>Incluye: {e(', '.join(subtajos))}</div>"
            filas += (f"<tr><td><b>{e(g.get('trabajo'))}</b>{sub_txt}"
                      f"<div style='font-size:11px;color:var(--muted);'>Orden {e(g.get('orden_ejecucion'))} · {e(g.get('fase_nombre'))}</div></td>"
                      f"<td>{e(g.get('propiedad'))}</td><td><b>{e(g.get('n_ubicaciones'))}</b></td>"
                      f"<td>{_ubicaciones_html(g.get('ubicaciones', []))}</td>"
                      f"<td>{e(g.get('estado_actual'))}</td><td style='font-size:12px;'>{e(g.get('motivo'))}</td></tr>")
        if not filas:
            filas = '<tr><td colspan="6" class="empty">Sin tajos en esta sección.</td></tr>'
        titulo_seccion = titulo  # el recuento ya vive en el centro de mando de arriba
        contenido = (
            f"<p style='font-size:12px;color:var(--muted);margin-bottom:8px;'>{explicacion}</p>"
            "<div class='table-scroll'><table class='data'><thead><tr><th>Tajo agrupado</th>"
            "<th>Responsable</th><th>Ubicaciones</th><th>Dónde</th><th>Estado</th><th>Motivo</th>"
            f"</tr></thead><tbody>{filas}</tbody></table></div>")
        id_ancla = f'sec-inv-{codigo.lower()}'
        inventario_por_codigo[codigo] = {
            'id': id_ancla,
            'html': _envolver_plegable(id_ancla, titulo_seccion, contenido),
            'n': len(grupos),
        }

    titulo_ejecucion = "Qué hacer ahora: orden lógico de ejecución"
    contenido_ejecucion = f"""<p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">Primero aparecen los tajos viables de viviendas, después zonas comunes y edificio. Los tajos iguales se agrupan. VERIFICAR nunca se considera ejecutable hasta confirmar la duda. <a href="prioridades_trabajos.json" target="_blank">Ver cálculo y detalle completo</a>.</p>
      <div style="margin-bottom:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:12px;color:var(--muted);">Filtrar:</span>
        <select id="filtro-sit" style="font-size:12px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;">
          <option value="">LISTO + VERIFICAR</option>
          <option value="LISTO">Solo LISTO</option>
          <option value="VERIFICAR">Solo VERIFICAR</option>
        </select>
        <span id="prio-count" style="font-size:12px;color:var(--muted);"></span>
      </div>
      <section id="timeline-prio" class="timeline-prio" aria-label="Orden lógico de ejecución">
        {tarjetas_prio}
      </section>"""
    ejecucion_html = _envolver_plegable(
        _ID_SEC_EJECUCION, titulo_ejecucion, contenido_ejecucion,
        color_borde='var(--ok)')

    secciones_indice = []
    if tareas_manual_html:
        secciones_indice.append({
            'id': _ID_SEC_TAREAS,
            'etiqueta': (f"Tareas manuales — "
                        f"{n_tareas_pendientes} pendientes"),
            'grupo': 'actuar', 'color': 'var(--accent2)',
        })
    else:
        # La tarjeta del centro de mando enlaza siempre a #sec-tareas: sin
        # esto, una obra sin tareas manuales dejaria ese enlace apuntando a
        # una seccion que no existe en la pagina.
        tareas_manual_html = _envolver_plegable(
            _ID_SEC_TAREAS, 'Tareas manuales',
            '<p style="color:var(--muted);font-size:13px;">No hay tareas '
            'manuales declaradas en la ficha.</p>')
    secciones_indice.append({
        'id': _ID_SEC_DUDAS,
        'etiqueta': f"Preguntas pendientes antes de decidir — {len(dudas_prio)}",
        'grupo': 'actuar',
        'color': 'var(--warn)' if dudas_prio else 'var(--ok)',
    })
    secciones_indice.append({
        'id': _ID_SEC_EJECUCION,
        'etiqueta': f"Qué hacer ahora — {resumen_prio.get('listos', 0)} tajos listos",
        'grupo': 'actuar', 'color': 'var(--ok)',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['BLOQUEADO']['id'],
        'etiqueta': f"Tajos bloqueados — {inventario_por_codigo['BLOQUEADO']['n']}",
        'grupo': 'actuar', 'color': 'var(--warn)',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['SIN_REVISAR']['id'],
        'etiqueta': f"Sin revisar nunca — {inventario_por_codigo['SIN_REVISAR']['n']}",
        'grupo': 'actuar', 'color': 'var(--bad)',
    })
    if orden_html:
        secciones_indice.append({
            'id': _ID_SEC_PREGUNTAS_CATALOGO,
            'etiqueta': (f"Preguntas sobre el catálogo — "
                        f"{len(prioridades.get('preguntas_orden') or [])}"),
            'grupo': 'consulta', 'color': 'var(--warn)',
        })
    if prevision_html:
        secciones_indice.append({
            'id': _ID_SEC_PREVISION,
            'etiqueta': 'Qué se desbloquea al terminar cada cosa',
            'grupo': 'consulta',
        })
    secciones_indice.append({
        'id': inventario_por_codigo['VIABLE']['id'],
        'etiqueta': f"Tajos viables (inventario) — {inventario_por_codigo['VIABLE']['n']}",
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['OTROS_GREMIOS']['id'],
        'etiqueta': (f"Otros gremios e interferencias — "
                    f"{inventario_por_codigo['OTROS_GREMIOS']['n']}"),
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['DUDAS']['id'],
        'etiqueta': f"Sin clasificar o por verificar — {inventario_por_codigo['DUDAS']['n']}",
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['TERMINADO']['id'],
        'etiqueta': f"Tajos terminados — {inventario_por_codigo['TERMINADO']['n']}",
        'grupo': 'consulta',
    })
    secciones_consulta = [
        seccion for seccion in secciones_indice
        if seccion.get('grupo') == 'consulta'
    ]
    id_terminados = inventario_por_codigo['TERMINADO']['id']
    if not any(s.get('id') == id_terminados for s in secciones_consulta):
        secciones_consulta.append({
            'id': id_terminados,
            'etiqueta': (f"Tajos terminados — "
                         f"{inventario_por_codigo['TERMINADO']['n']}"),
            'color': 'var(--muted)',
        })
    chips_consulta_html = ''.join(
        f"<a class='bento-chip indice-nav-link' "
        f"href='#{_e_atributo(seccion['id'])}' "
        f"data-abre='{_e_atributo(seccion['id'])}' "
        f"style='--bento-color:{seccion.get('color') or 'var(--muted)'};'>"
        f"<span>{e(seccion['etiqueta'])}</span></a>"
        for seccion in secciones_consulta
    )

    categorias_salud = [
        ('Listos', n_listos_real, 'var(--ok)'),
        ('Verificar', n_verificar_real, 'var(--warn)'),
        ('Bloqueados', resumen_prio.get('bloqueados', 0), 'var(--warn)'),
        ('Otros gremios', resumen_prio.get('otros_gremios', 0), 'var(--muted)'),
        ('Sin revisar nunca', resumen_prio.get('sin_revisar', 0), 'var(--bad)'),
        ('Terminados', resumen_prio.get('terminados', 0), 'var(--muted)'),
    ]
    segmentos_salud = ''.join(
        f"<span class='bento-segment' "
        f"style='flex:{cantidad} 1 0;background:{color};' "
        f"title='{_e_atributo(etiqueta)}: {_e_atributo(cantidad)}'></span>"
        for etiqueta, cantidad, color in categorias_salud if cantidad
    )
    leyenda_salud = ''.join(
        f"<div class='bento-legend-item' style='--bento-color:{color};'>"
        f"<div class='bento-legend-label'><span class='bento-dot'></span>"
        f"<span>{e(etiqueta)}</span></div><strong>{e(cantidad)}</strong></div>"
        for etiqueta, cantidad, color in categorias_salud
    )

    n_bloqueados = resumen_prio.get('bloqueados', 0)
    n_preguntas = resumen_prio.get('preguntas_pendientes', 0)
    atencion_requerida = n_bloqueados > 0 or n_preguntas > 0
    if atencion_requerida:
        atencion_titulo = 'Atención requerida'
        atencion_detalle = (
            'Se activa porque bloqueados > 0 o preguntas pendientes > 0: '
            f'{n_bloqueados} bloqueados · {n_preguntas} preguntas pendientes.')
        atencion_clase = ''
    else:
        atencion_titulo = 'Sin atención requerida'
        atencion_detalle = (
            f'No se activa: bloqueados = {n_bloqueados} y preguntas '
            f'pendientes = {n_preguntas}.')
        atencion_clase = ' is-ok'

    avance_html = '—' if avance_pct is None else f'{e(avance_pct)}%'

    grupo_actuar_html = (
        tareas_manual_html + dudas_html + ejecucion_html
        + inventario_por_codigo['BLOQUEADO']['html']
        + inventario_por_codigo['SIN_REVISAR']['html']
    )
    grupo_consulta_html = (
        orden_html + prevision_html
        + inventario_por_codigo['VIABLE']['html']
        + inventario_por_codigo['OTROS_GREMIOS']['html']
        + inventario_por_codigo['DUDAS']['html']
        + inventario_por_codigo['TERMINADO']['html']
    )

    bento_command = f"""
    <section class="bento-command" aria-label="Centro de mando de prioridades">
      <div class="bento-health">
        <div class="bento-health-top">
          <div>
            <span class="bento-eyebrow">Centro de mando · Prioridades</span>
            <h2>Estado del proyecto</h2>
            <p class="bento-health-meta">Revisión utilizada: {e(prioridades.get('revision'))} · Motor v{e(prioridades.get('version'))} · catálogo v{e(prioridades.get('catalogo_version'))}</p>
          </div>
          <div class="bento-health-side">
            <div class="bento-attention{atencion_clase}">
              <strong>{e(atencion_titulo)}</strong>
              <span>{e(atencion_detalle)}</span>
            </div>
            <div class="bento-stat"><strong>{e(resumen_prio.get('inventario_total', 0))}</strong><span>tipos de tajo agrupados</span></div>
            <div class="bento-stat"><strong>{avance_html}</strong><span>completado · avance estimado</span></div>
          </div>
        </div>
        <div class="bento-segments" role="img" aria-label="Distribución de la salud del proyecto">{segmentos_salud}</div>
        <div class="bento-legend">{leyenda_salud}</div>
      </div>

      <div class="bento-grid">
        <a class="bento-link bento-card bento-hero indice-nav-link" href="#{_ID_SEC_EJECUCION}" data-abre="{_ID_SEC_EJECUCION}">
          <div class="bento-hero-head">
            <div>
              <div class="bento-card-kicker"><span class="bento-dot"></span>Acción principal</div>
              <h3>Qué hacer ahora</h3>
              <p class="bento-card-copy">Orden lógico de ejecución de tajos</p>
            </div>
            <div class="bento-hero-total"><strong>{e(n_listos_real)}</strong><span>tajos listos</span></div>
          </div>
          <div class="bento-breakdown">
            <div class="bento-breakdown-item" style="--bento-color:var(--ok);"><span>Listos</span><strong>{e(n_listos_real)}</strong></div>
            <div class="bento-breakdown-item" style="--bento-color:var(--warn);"><span>Verificar</span><strong>{e(n_verificar_real)}</strong></div>
          </div>
        </a>

        <a class="bento-link bento-card bento-small indice-nav-link" style="--bento-color:var(--warn);" href="#{inventario_por_codigo['BLOQUEADO']['id']}" data-abre="{inventario_por_codigo['BLOQUEADO']['id']}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Dependencias</div><h3>Tajos bloqueados</h3>
          <div class="bento-number">{e(n_bloqueados)}</div><div class="bento-number-label">tajos propios con dependencias</div>
        </a>

        <a class="bento-link bento-card bento-small indice-nav-link" style="--bento-color:var(--accent2);" href="#{_ID_SEC_TAREAS}" data-abre="{_ID_SEC_TAREAS}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Manual</div><h3>Tareas manuales</h3>
          <div class="bento-number">{n_tareas_pendientes}</div><div class="bento-number-label">pendientes declaradas en la ficha</div>
        </a>

        <a class="bento-link bento-card bento-half indice-nav-link" style="--bento-color:var(--bad);" href="#{inventario_por_codigo['SIN_REVISAR']['id']}" data-abre="{inventario_por_codigo['SIN_REVISAR']['id']}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Revisar</div><h3>Sin revisar nunca</h3>
          <div class="bento-number">{e(resumen_prio.get('sin_revisar', 0))}</div><div class="bento-number-label">tajos que nadie ha mirado todavía · {e(resumen_prio.get('unidades_sin_revisar', 0))} celdas</div>
        </a>

        <a class="bento-link bento-card bento-half indice-nav-link" style="--bento-color:{'var(--warn)' if n_preguntas else 'var(--ok)'};" href="#{_ID_SEC_DUDAS}" data-abre="{_ID_SEC_DUDAS}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Decisiones</div><h3>Preguntas pendientes</h3>
          <div class="bento-number">{e(n_preguntas)}</div><div class="bento-number-label">resolver antes de decidir</div>
        </a>
      </div>

      <nav class="bento-reference" aria-label="Consulta y referencia">
        <div class="bento-reference-title">Consulta y referencia</div>
        <div class="bento-chips">{chips_consulta_html}</div>
      </nav>
    </section>"""

    return {
        'bento_command': bento_command,
        'estado_obra_html': estado_obra_html,
        'avisos_prio': avisos_prio,
        'script_indice': _SCRIPT_INDICE_PRIORIDADES,
        'tareas_manual_html': tareas_manual_html,
        'dudas_html': dudas_html,
        'ejecucion_html': ejecucion_html,
        'bloqueado_html': inventario_por_codigo['BLOQUEADO']['html'],
        'sin_revisar_html': inventario_por_codigo['SIN_REVISAR']['html'],
        'orden_html': orden_html,
        'prevision_html': prevision_html,
        'viable_html': inventario_por_codigo['VIABLE']['html'],
        'otros_gremios_html': inventario_por_codigo['OTROS_GREMIOS']['html'],
        'dudas_inventario_html': inventario_por_codigo['DUDAS']['html'],
        'terminado_html': inventario_por_codigo['TERMINADO']['html'],
    }


def bloque_prioridades(prioridades, tareas_manual=None, documentos=None,
                       obra='', avance_pct=None):
    """HTML de la pestana Prioridades — envoltorio sobre
    bloque_prioridades_partes() que reconstruye el string de siempre.

    Separado de generar_panel para poder probarlo sin montar una obra entera:
    un dato que se calcula y no se pinta es lo mismo que no calcularlo.
    """
    partes = bloque_prioridades_partes(
        prioridades, tareas_manual=tareas_manual, documentos=documentos,
        obra=obra, avance_pct=avance_pct)
    if isinstance(partes, str):
        return partes
    return (
        partes['bento_command']
        + partes['estado_obra_html']
        + partes['avisos_prio']
        + partes['script_indice']
        + partes['tareas_manual_html']
        + partes['dudas_html']
        + partes['ejecucion_html']
        + partes['bloqueado_html']
        + partes['sin_revisar_html']
        + partes['orden_html']
        + partes['prevision_html']
        + partes['viable_html']
        + partes['otros_gremios_html']
        + partes['dudas_inventario_html']
        + partes['terminado_html']
    )


def generar_panel(obra, subtitulo, historial, materiales, ficha, documentos,
                  output_path, volver_href="../../index.html", prioridades=None,
                  tajos_memoria=None, mem_resumen=None, bat_path=None,
                  cierre=None, cierre_avisos=None):
    prioridades = prioridades or {}
    snapshot = historial[-1][1] if historial else []
    historial_panel = list(historial)
    historial_confirmado = bool(prioridades.get('historial_confirmado_terminado'))
    if historial_confirmado and snapshot:
        snapshot = [{**registro, 'status': 'X'} for registro in snapshot]
        historial_panel[-1] = (historial_panel[-1][0], snapshot)

    kpis = motor.kpis_snapshot(snapshot) if snapshot else {}
    bloqueos = [] if historial_confirmado else (motor.detectar_bloqueos(snapshot) if snapshot else [])
    sin_cambios = False if historial_confirmado else motor.sin_cambios_entre_ultimas(historial)
    n_bloqueos_base = (prioridades.get('resumen') or {}).get(
        'bloqueados', len(bloqueos))

    payload = {
        'serie': motor.serie_tiempo(historial_panel) if historial_panel else [],
        'por_planta': motor.matriz_planta_edificio(snapshot) if snapshot else {'labels': [], 'series': {}},
        'por_tarea': motor.ranking_tareas_con_memoria(snapshot, tajos_memoria) if snapshot else [],
    }

    # ---- Banners globales ----
    banners = ""
    if historial_confirmado:
        banners += ('<div class="banner"><b>Estado confirmado:</b> obra entregada y en funcionamiento. '
                    'Solo queda revisar el alcance postapertura de los apartamentos 1 y 2 de planta baja '
                    'cuando termine el tabique separador de cocinas.</div>')
    if sin_cambios:
        banners += ('<div class="banner bad">⚠ Las dos últimas revisiones registradas son idénticas: '
                    'posible hoja de campo sin actualizar.</div>')
    if materiales.get('aviso'):
        banners += f'<div class="banner">⚠ {materiales["aviso"]}</div>'
    if not ficha.get('_disponible'):
        banners += ('<div class="banner">ℹ No se encontró <b>FICHA DE OBRA.xlsx</b> en la carpeta. '
                    'Las secciones Personal, Hitos y Riesgos manuales estarán vacías hasta que la rellenes.</div>')

    # ---- PANEL (resumen) ----
    datos = ficha.get('datos', {})
    def d(k, default='—'):
        v = datos.get(k, '')
        return v if v else default
    resumen_datos = ''.join(
        f'<tr><td style="color:var(--muted);width:42%;">{k}</td><td>{v or "—"}</td></tr>'
        for k, v in datos.items()
    ) or '<tr><td class="empty">Sin ficha de obra.</td></tr>'

    kpi_html = ""
    if kpis:
        kpi_html = f"""
        <div class="kpi"><div class="label">Avance estricto (X)</div><div class="value">{kpis['pct_estricto']}%</div><div class="hint">Solo tareas 100% terminadas</div></div>
        <div class="kpi"><div class="label">Avance estimado</div><div class="value">{kpis['pct_ponderado']}%</div><div class="hint">Incluye parciales (estimación)</div></div>
        <div class="kpi"><div class="label">Revisiones</div><div class="value">{len(historial)}</div><div class="hint">Desde {historial[0][0]}</div></div>
        <div class="kpi"><div class="label">Tajos bloqueados</div><div class="value">{n_bloqueos_base}</div><div class="hint">Sagarde · dependencias de la base</div></div>
        """
    else:
        kpi_html = '<div class="kpi"><div class="label">Avance</div><div class="value">—</div><div class="hint">Sin datos de revisión</div></div>'

    # ---- TRABAJOS: desviaciones + ranking + detalle (charts via JS) ----
    filas_bloq = ""
    if bloqueos:
        for b in bloqueos:
            badge = 'bad' if b['avance'] < 30 else 'warn'
            filas_bloq += (f"<tr><td>{b['tipo']}</td><td>{b['edificio']}</td><td>{b['planta']}</td>"
                           f"<td>{b['unidad']}</td><td><span class='badge {badge}'>{b['avance']}%</span></td>"
                           f"<td>{b['motivo']}</td></tr>")
    else:
        filas_bloq = '<tr><td colspan="6" class="empty">No se detectan desviaciones de avance con la heurística actual.</td></tr>'

    detalle = motor.tabla_detalle(snapshot) if snapshot else []
    filas_det = "".join(
        f"<tr><td>{r['edificio']}</td><td>{r['planta']}</td><td>{r['pct_estricto']}%</td>"
        f"<td>{r['pct_ponderado']}%</td><td>{r['n']}</td></tr>" for r in detalle
    ) or '<tr><td colspan="5" class="empty">Sin datos.</td></tr>'

    # ---- MATERIALES ----
    if materiales.get('disponible') and materiales.get('items'):
        filas_mat = ""
        cat_actual = None
        for it in materiales['items']:
            if it['categoria'] != cat_actual:
                cat_actual = it['categoria']
                if cat_actual:
                    filas_mat += f"<tr><td colspan='4' style='font-weight:700;color:var(--header2);background:#f4f6f9;'>{cat_actual}</td></tr>"
            filas_mat += (f"<tr><td>{it['material']}</td><td>{it['tipo']}</td>"
                          f"<td>{it['uni']}</td><td style='text-align:right;'>{_fmt_num(it['total'])}</td></tr>")
        mat_meta = (f"Última hoja: <b>{materiales['ultimo_mes']}</b>"
                    + (f" · última entrada {materiales['ultima_fecha']}" if materiales.get('ultima_fecha') else ""))
        materiales_html = f"""
        <div class="card"><h3>Consumo acumulado de material — {materiales['ultimo_mes']}</h3>
        <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">{mat_meta}. Cantidades <b>suministradas</b> según hoja; no equivalen necesariamente a material instalado.</p>
        <table class="data"><thead><tr><th>Material</th><th>Tipo</th><th>Uni</th><th style="text-align:right;">Total</th></tr></thead>
        <tbody>{filas_mat}</tbody></table></div>"""
    elif materiales.get('disponible'):
        materiales_html = f'<div class="card"><h3>Materiales</h3><p class="empty">Se encontró la hoja de materiales pero no se pudo interpretar automáticamente ({materiales.get("aviso") or "formato no reconocido"}). Ábrela desde la sección Documentos.</p></div>'
    else:
        materiales_html = '<div class="card"><h3>Materiales</h3><p class="empty">No se encontró hoja de materiales en la carpeta de la obra.</p></div>'

    # ---- PERSONAL / PLAN / HITOS / RIESGOS (de ficha) + riesgos auto ----
    def tabla_ficha(registros, cols_orden=None):
        if not registros:
            return '<p class="empty">Sin datos en la ficha de obra.</p>'
        cols = cols_orden or list(registros[0].keys())
        head = "".join(f"<th>{c}</th>" for c in cols)
        body = ""
        for reg in registros:
            body += "<tr>" + "".join(f"<td>{reg.get(c,'')}</td>" for c in cols) + "</tr>"
        return f'<table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'

    personal_html = tabla_ficha(ficha.get('personal', []))
    hitos_html = tabla_ficha(ficha.get('hitos', []))

    # ---- PRIORIDADES E INVENTARIO COMPLETO DE TAJOS (motor v4) ----
    partes_prioridades = bloque_prioridades_partes(
        prioridades, tareas_manual=ficha.get('tareas', []),
        documentos=documentos, obra=obra,
        avance_pct=kpis.get('pct_ponderado'))
    if isinstance(partes_prioridades, str):
        prioridades_html = partes_prioridades
        secciones_prioridades = {}
    else:
        prioridades_html = (
            partes_prioridades['bento_command']
            + partes_prioridades['estado_obra_html']
            + partes_prioridades['avisos_prio']
            + partes_prioridades['script_indice']
            + partes_prioridades['tareas_manual_html']
            + partes_prioridades['dudas_html']
            + partes_prioridades['ejecucion_html']
            + partes_prioridades['bloqueado_html']
            + partes_prioridades['sin_revisar_html']
            + partes_prioridades['orden_html']
            + partes_prioridades['prevision_html']
            + partes_prioridades['viable_html']
            + partes_prioridades['otros_gremios_html']
            + partes_prioridades['dudas_inventario_html']
            + partes_prioridades['terminado_html']
        )
        secciones_prioridades = {
            'estado_proyecto': (
                partes_prioridades['bento_command']
                + partes_prioridades['estado_obra_html']
                + partes_prioridades['avisos_prio']),
            'que_hacer_ahora': partes_prioridades['ejecucion_html'],
            'tajos_bloqueados': partes_prioridades['bloqueado_html'],
            'tareas_manuales': partes_prioridades['tareas_manual_html'],
            'sin_revisar': partes_prioridades['sin_revisar_html'],
        }

    # Se reconstruye desde la base/priorizador del mismo ciclo. La ficha XLSX
    # solo aporta el registro manual complementario.
    riesgos_html = bloque_riesgos(
        prioridades, bloqueos=bloqueos,
        riesgos_manual=ficha.get('riesgos', []), sin_cambios=sin_cambios)
    cierre_html = bloque_cierre(cierre, avisos=cierre_avisos)

    # ---- DOCUMENTOS ----
    docs_html = ""
    if documentos:
        cat_actual = None
        for doc in documentos:
            if doc['categoria'] != cat_actual:
                cat_actual = doc['categoria']
                docs_html += f'<div class="doc-cat">{cat_actual}</div>'
            sub = f" <span style='color:var(--muted);font-size:11.5px;'>· {doc['subcarpeta']}</span>" if doc['subcarpeta'] else ""
            docs_html += (f'<div class="doc"><a href="{doc["href"]}" target="_blank">{doc["nombre"]}</a>'
                          f'<span style="color:var(--muted);font-size:11.5px;"> ({doc["kb"]} KB)</span>{sub}</div>')
    else:
        docs_html = '<p class="empty">No se encontraron documentos en la carpeta de la obra.</p>'

    norm_html = "".join(f"<li>{n}</li>" for n in NORMATIVA_ITEMS)

    # ---- ACTUALIZAR ----
    mem_r = mem_resumen or {}
    bat_rel = '../../_SISTEMA INFORME SAGARDE IA/Actualizar_Obras.bat'
    bat_abs = bat_path or ''
    bat_js = bat_abs.replace('\\', '\\\\').replace("'", '')  # seguro en atributo onclick JS
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
    mem_nota = ''
    if tajos_memoria:
        n_act = mem_r.get('activos', sum(1 for v in tajos_memoria.values() if not v.get('terminado')))
        n_term = mem_r.get('terminados', sum(1 for v in tajos_memoria.values() if v.get('terminado')))
        mem_nota = (f'<div style="margin-top:18px;"><b>Memoria de tajos</b>: '
                    f'{len(tajos_memoria)} tajos en total &mdash; '
                    f'<span style="color:var(--ok);">{n_act} activos</span> · '
                    f'<span style="color:var(--muted);">{n_term} terminados (100% forzado en el gráfico)</span>.</div>'
                    f'<p style="font-size:12px;color:var(--muted);margin-top:6px;">'
                    f'Los tajos terminados son aquellos que desaparecieron de la hoja de revisión. '
                    f'Se conservan en <code>memoria_obra.json</code> y se muestran al 100% en el gráfico de avance.</p>')
    actualizar_html = f"""<div class="card">
  <h3>↻ Actualizar panel</h3>
  <p style="font-size:13px;">Este panel es un fichero HTML estático. Se actualizó el <b>{fecha_gen}</b>.
  Para reflejarlo con los últimos archivos de revisión hay que regenerarlo.</p>
  <div style="margin-top:18px;background:#f0f4ff;border:1px solid #c0cfe8;border-radius:8px;padding:14px 18px;">
    <b style="font-size:13px;">Paso 1 &mdash; Haz doble clic en este archivo:</b><br>
    <code style="font-size:13px;display:block;margin:8px 0;">Actualizar_Obras.bat</code>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">
      <a href="{bat_rel}" style="background:var(--header2);color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;">⬇ Abrir / descargar .bat</a>
      <button onclick="navigator.clipboard.writeText('{bat_js}').then(()=>this.textContent='✓ Copiado!').catch(()=>this.textContent='Error')" style="background:#e8f0fe;border:1px solid #c0cfe8;padding:7px 14px;border-radius:6px;font-size:13px;cursor:pointer;">📋 Copiar ruta completa</button>
    </div>
    {('<div style="font-size:11.5px;color:var(--muted);margin-top:6px;">Ruta: <code>' + html_lib.escape(bat_abs) + '</code></div>') if bat_abs else ''}
  </div>
  <div style="margin-top:18px;background:#f4f6f9;border-radius:8px;padding:14px 18px;">
    <b style="font-size:13px;">Paso 2 &mdash; Recarga esta página en el navegador (F5)</b><br>
    <span style="font-size:12.5px;color:var(--muted);">El .bat regenera el panel.html y abre el índice automáticamente.</span>
  </div>
  {mem_nota}
</div>"""

    # ---- INFORME DE OBRA A LA CARTA ----
    # Cada valor es la MISMA cadena HTML que ya pinta la pestana
    # correspondiente. No se recalcula ninguna cifra por un camino nuevo:
    # es la salvaguarda contra la familia de fallo de este proyecto
    # (un dato declarado que un camino distinto ignora en silencio).
    secciones_informe = {
        'trabajos': (
            "<div class='card'><h3>Desviaciones de avance</h3>"
            "<table class='data'><thead><tr><th>Tipo</th><th>Edificio</th>"
            "<th>Planta</th><th>Unidad</th><th>Avance</th><th>Motivo</th>"
            f"</tr></thead><tbody>{filas_bloq}</tbody></table></div>"
            "<div class='card'><h3>Detalle por planta / edificio</h3>"
            "<table class='data'><thead><tr><th>Edificio</th><th>Planta</th>"
            "<th>% estricto</th><th>% estimado</th><th>Nº registros</th>"
            f"</tr></thead><tbody>{filas_det}</tbody></table></div>"
        ),
        'materiales': materiales_html,
        'personal': f"<div class='card'><h3>Personal asignado</h3>{personal_html}</div>",
        'prioridades': secciones_prioridades,
        'riesgos': riesgos_html,
        'normativa': (
            "<div class='card'><h3>Normativa y criterios técnicos "
            "aplicables</h3><p style='font-size:12.5px;color:var(--muted);"
            "margin-bottom:8px;'>Lista de referencia. No sustituye la "
            "comprobación de la versión vigente ni las instrucciones de la "
            f"Dirección Facultativa.</p><ul class='norm'>{norm_html}</ul></div>"
        ),
        'documentos': f"<div class='card'><h3>Documentos de la obra</h3>{docs_html}</div>",
        'cierre': cierre_html,
    }
    secciones_json = json.dumps(secciones_informe, ensure_ascii=False).replace('</script>', '<\\/script>')

    data_json = json.dumps(payload, ensure_ascii=False).replace('</script>', '<\\/script>')

    # ---- HTML ----
    pdf_ejecutivo_nombre = f"INFORME_EJECUTIVO_{obra.replace(' ', '_')}.pdf"
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel Sagarde IA · {obra}</title>
<script src="../../_SISTEMA INFORME SAGARDE IA/static/chart.min.js"></script>
<script id="secciones-informe" type="application/json">{secciones_json}</script>
<style>{ESTILOS}</style></head><body><div class="wrap">
<div class="header">
  <div><div class="brand">Informe Sagarde IA · Panel de obra</div><h1>{obra}</h1><div class="sub">{subtitulo}</div></div>
  <div class="meta">Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
  Última revisión: {historial[-1][0] if historial else '—'}<br>
  <a class="volver" href="{volver_href}">← Todas las obras</a>
  <a class="volver" href="{pdf_ejecutivo_nombre}" target="_blank" style="background:var(--bad);border-color:var(--bad);margin-left:6px;">📄 Informe Ejecutivo PDF</a>
  <a class="volver" id="btn-informe-obra" href="#panel-informe-obra" style="background:var(--accent);border-color:var(--accent);color:#1c2733;margin-left:6px;" onclick="abrirSelectorInforme();return true;">📋 Informe de obra</a></div>
</div>

<div id="panel-informe-obra" class="card" style="display:none;">
  <h3>Informe de obra — elige qué secciones incluir</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">
    Se genera con los datos de esta misma página (tan actualizado como la
    última vez que se regeneró el panel). Marca lo que quieras enseñar,
    dale a vista previa y desde ahí puedes imprimir o guardar como PDF.
  </p>
  <div id="informe-obra-grupos">
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="trabajos" onchange="toggleGrupoInforme(this)"> <b>✓ Trabajos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="materiales" onchange="toggleGrupoInforme(this)"> <b>▣ Materiales</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="personal" onchange="toggleGrupoInforme(this)"> <b>👷 Personal</b></label>
    <div class="tj-group-hdr">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
        <input type="checkbox" id="cb-prioridades-all" onchange="toggleGrupoPrioridades(this)"> <b>🎯 Prioridades</b>
      </label>
    </div>
    <div class="tj-items" style="padding-left:26px;">
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="estado_proyecto"> Estado del proyecto</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="que_hacer_ahora"> Qué hacer ahora</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="tajos_bloqueados"> Tajos bloqueados</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="tareas_manuales"> Tareas manuales</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="sin_revisar"> Sin revisar nunca</label>
    </div>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="riesgos" onchange="toggleGrupoInforme(this)"> <b>⚠ Riesgos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="normativa" onchange="toggleGrupoInforme(this)"> <b>📘 Normativa</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="documentos" onchange="toggleGrupoInforme(this)"> <b>📎 Documentos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="cierre" onchange="toggleGrupoInforme(this)"> <b>📋 Cierre</b></label>
  </div>
  <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
    <button type="button" onclick="marcarTodoInforme()" style="background:#eef0f4;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;">Marcar todo</button>
    <button type="button" onclick="generarVistaPreviaInforme()" style="background:var(--accent);border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;">👁 Vista previa</button>
  </div>
</div>

<div class="nav">
  <button class="active" data-view="v-panel">▦ Panel</button>
  <button data-view="v-trabajos">✓ Trabajos</button>
  <button data-view="v-materiales">▣ Materiales</button>
  <button data-view="v-personal">👷 Personal</button>
  <button data-view="v-prioridades">🎯 Prioridades</button>
  <button data-view="v-riesgos">⚠ Riesgos</button>
  <button data-view="v-normativa">📘 Normativa</button>
  <button data-view="v-docs">📎 Documentos</button>
  <button data-view="v-cierre">📋 Cierre</button>
  <button data-view="v-actualizar" style="margin-left:auto;background:var(--header2);color:#fff;">↻ Actualizar</button>
</div>

{banners}

<section id="v-panel" class="view active">
  <div class="kpi-row">{kpi_html}</div>
  <div class="chart-row">
    <div class="card"><h3>Evolución del avance</h3><canvas id="chartSerie"></canvas></div>
    <div class="card"><h3>Avance por planta y edificio</h3><canvas id="chartPlanta"></canvas></div>
  </div>
  <div class="card"><h3>Ficha de obra</h3><table class="data"><tbody>{resumen_datos}</tbody></table></div>
</section>

<section id="v-trabajos" class="view">
  <div class="card"><h3>Avance por tarea — cuellos de botella</h3><canvas id="chartTareas" style="max-height:520px;"></canvas></div>
  <div class="card"><h3>Desviaciones de avance</h3>
    <table class="data"><thead><tr><th>Tipo</th><th>Edificio</th><th>Planta</th><th>Unidad</th><th>Avance</th><th>Motivo</th></tr></thead>
    <tbody>{filas_bloq}</tbody></table></div>
  <div class="card"><h3>Detalle por planta / edificio</h3>
    <table class="data"><thead><tr><th>Edificio</th><th>Planta</th><th>% estricto</th><th>% estimado</th><th>Nº registros</th></tr></thead>
    <tbody>{filas_det}</tbody></table></div>
</section>

<section id="v-materiales" class="view">{materiales_html}</section>

<section id="v-personal" class="view"><div class="card"><h3>Personal asignado</h3>{personal_html}</div></section>

<section id="v-prioridades" class="view">{prioridades_html}
  <div class="card"><h3>Hitos manuales</h3>{hitos_html}</div></section>

<section id="v-riesgos" class="view">{riesgos_html}</section>

<section id="v-normativa" class="view"><div class="card"><h3>Normativa y criterios técnicos aplicables</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:8px;">Lista de referencia. No sustituye la comprobación de la versión vigente ni las instrucciones de la Dirección Facultativa.</p>
  <ul class="norm">{norm_html}</ul></div></section>

<section id="v-docs" class="view"><div class="card"><h3>Documentos de la obra</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:8px;">Todos los archivos de la carpeta. Clic para abrir (los enlaces funcionan en el PC; en el móvil abre los archivos desde la app de OneDrive).</p>
  {docs_html}</div></section>

<section id="v-cierre" class="view">{cierre_html}</section>

<section id="v-actualizar" class="view">{actualizar_html}</section>

<div class="footer">Informe Sagarde IA · Generado automáticamente a partir de los archivos de la carpeta de la obra. Los porcentajes, bloqueos y prioridades son cálculos de apoyo; no sustituyen la verificación en obra.</div>
</div>
<script>
const DATA = {data_json};
document.querySelectorAll('.nav button').forEach(btn=>btn.addEventListener('click',()=>{{
  document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.view).classList.add('active');
}}));
function pctColor(p){{return p<40?'#d9483c':p<70?'#e07b1a':'#2e9e5b';}}
if(DATA.serie.length) new Chart(document.getElementById('chartSerie'),{{type:'line',
  data:{{labels:DATA.serie.map(d=>d.fecha),datasets:[
    {{label:'% estricto',data:DATA.serie.map(d=>d.pct_estricto),borderColor:'#123a63',backgroundColor:'#123a6320',borderWidth:2,tension:.25,fill:true,pointRadius:2}},
    {{label:'% estimado',data:DATA.serie.map(d=>d.pct_ponderado),borderColor:'#f5a524',borderWidth:2,borderDash:[5,3],tension:.25,pointRadius:2}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
if(Object.keys(DATA.por_planta.series).length){{
  const eds=Object.keys(DATA.por_planta.series),col=['#123a63','#f5a524','#2e7dd7','#8172B3'];
  new Chart(document.getElementById('chartPlanta'),{{type:'bar',
    data:{{labels:DATA.por_planta.labels,datasets:eds.map((e,i)=>({{label:e,data:DATA.por_planta.series[e],backgroundColor:col[i%col.length]}}))}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
}}
if(DATA.por_tarea.length) new Chart(document.getElementById('chartTareas'),{{type:'bar',
  data:{{labels:DATA.por_tarea.map(t=>t[0]),datasets:[{{label:'% avance',data:DATA.por_tarea.map(t=>t[1]),backgroundColor:DATA.por_tarea.map(t=>pctColor(t[1]))}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
function filtrarPrio(){{
  const fase=document.getElementById('filtro-fase')?.value||'';
  const sit=document.getElementById('filtro-sit')?.value||'';
  const items=document.querySelectorAll('#timeline-prio .timeline-item[data-fase]');
  const visibles=[];
  let n=0;
  items.forEach(item=>{{
    const ok=(!fase||item.dataset.fase===fase)&&(!sit||item.dataset.sit===sit);
    item.hidden=!ok;
    item.classList.remove('last-visible');
    if(ok){{visibles.push(item);n++;}}
    else{{const card=item.querySelector('.task-card');if(card)card.open=false;}}
  }});
  if(visibles.length)visibles[visibles.length-1].classList.add('last-visible');
  const cnt=document.getElementById('prio-count');
  if(cnt)cnt.textContent=n+' bloque(s) visibles';
}}
document.getElementById('filtro-fase')?.addEventListener('change',filtrarPrio);
document.getElementById('filtro-sit')?.addEventListener('change',filtrarPrio);
filtrarPrio();
</script></body></html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return {
        'kpis': kpis, 'bloqueos': bloqueos, 'sin_cambios': sin_cambios,
        'n_docs': len(documentos), 'output_path': output_path,
        'materiales_aviso': materiales.get('aviso'),
        'prioridades': prioridades,
    }












