---
name: sagarde-cerrar-obra
description: Cerrar una obra de Sagarde y mandarla al archivo de obras cerradas dejando el entorno limpio. Usar cuando Bixente diga que una obra ha terminado, que se cierra, que pasa a obras cerradas, que la quite del panel de seguimiento, o pregunte cómo archivar una obra.
---

# Cerrar una obra

El panel es solo para obra en curso. Cuando una obra acaba, desaparece del
seguimiento y queda como carpeta consultable en Obras cerradas. El seguimiento
posterior, si lo hay, va por **postventa**, que es otro apartado.

Hacerlo a mano —mover la carpeta y ya— parece funcionar, pero deja la obra en
`registro_obras.py` avisando en cada publicación y su adaptador huérfano en
`adaptadores/`. Es lo que llevan haciendo Egurrola y Zorrozaure desde que se
cerraron.

## Antes de tocar nada

1. **Preguntar a Bixente si la obra está realmente cerrada.** El histórico no
   lo sabe: Orueta llevaba tiempo terminada y el sistema la daba al 99.7 %.
2. Mirar el informe, que no mueve nada:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python cerrar_obra.py <id_obra>
```

3. Enseñarle ese informe —avance, última revisión y desglose `X/M///P/?/N`— y
   que confirme.

Los `id` válidos salen del propio error si te equivocas, o de
`registro_obras.py`.

## Cerrarla

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python cerrar_obra.py <id_obra> --ejecutar
```

Hace cuatro cosas: archiva el adaptador dentro de la obra (`_SISTEMA/`), la
saca de `registro_obras.py`, mueve la carpeta a
`SAGARDE (OLD)/OBRAS CERRADAS` y escribe `_SISTEMA/cierre.json` con cómo
terminó: avance, desglose completo, última revisión y el commit desde el que
se cerró.

**Aborta sin mover nada** si la obra no está en el registro, si su carpeta no
existe, si ya hay una obra archivada con ese nombre, o si hay cambios sin
commitear en la carpeta de la obra, su adaptador o el registro.

## Después

1. Lanzar `Actualizar_Sagarde.bat` — **con la autorización de Bixente**: hace
   `git add -A` y publica.
2. Comprobar, y reportarle el antes/después:
   - la obra ya **no** está en `resumen_obras.json`
   - **sí** aparece en el índice de obras cerradas
   - las obras que quedan **no se han movido** de avance
   - las dos suites siguen verdes:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

```bash
cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests
```

## Lo que no se toca

- **`reglas/CATALOGO_TAJOS.json`.** Los tajos propios de una obra viven ahí y
  hay pruebas que dependen de ellos. El fichero **no está en git**: si se
  estropea, no hay forma de restaurarlo.
- **El `.gitignore`.** Sus reglas de lista blanca dejan de casar solas cuando
  la carpeta se mueve, que es justo el efecto buscado: la obra sale de lo
  publicado. Los ficheros siguen en disco y en el historial de git.
- **Postventa.** Otro apartado.

## Si hay que deshacerlo

El script imprime el comando exacto para devolver la carpeta a su sitio. Para
devolver la obra al registro, `git checkout -- registro_obras.py` mientras no
se haya publicado.
