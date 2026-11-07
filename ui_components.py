"""Composants visuels autonomes de Futsal Manager.

Ce module contient les widgets dessinés en Qt qui ne portent pas la logique métier.
"""
import re
import unicodedata

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QSize, Signal, QMimeData
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QPolygonF, QPainterPath, QBrush, QFontMetrics, QDrag, QIcon, QPixmap, QPalette
from PySide6.QtWidgets import *

from help_content import HELP_THEMES, HELP_TOPICS, THEME_INDEX, TOPIC_INDEX

class ClubIdentityPreview(QFrame):
    """Aperçu d'identité soigné : fond stade, écusson héraldique, maillot aux
    proportions réelles avec rayures CLIPPÉES dans le vêtement et ombre portée.
    Le tout tient dans un ratio 16:9 : rien n'est étiré."""

    RATIO_W, RATIO_H = 320.0, 180.0

    def __init__(self,parent=None):
        super().__init__(parent)
        self.primary="#1f8a4d"; self.secondary="#0f3d27"
        self.logo="shield"; self.kit="vertical"; self.club_name="VOTRE CLUB"
        self.setMinimumSize(300, 169)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def hasHeightForWidth(self): return True
    def heightForWidth(self,width): return int(max(200, width*self.RATIO_H/self.RATIO_W))
    def sizeHint(self):
        from PySide6.QtCore import QSize as _QS
        return _QS(440, int(440*self.RATIO_H/self.RATIO_W))

    def set_state(self,primary,secondary,logo,kit,name):
        self.primary=primary or "#1f8a4d"; self.secondary=secondary or "#0f3d27"
        self.logo=logo; self.kit=kit; self.club_name=name or "VOTRE CLUB"; self.update()

    # ---------------------------------------------------------------- dessin
    def _crest_path(self,box):
        x,y,w,h=box.x(),box.y(),box.width(),box.height()
        cx=x+w/2.0
        path=QPainterPath()
        path.moveTo(cx, y)
        path.lineTo(x+w*0.92, y+h*0.10)
        path.lineTo(x+w*0.92, y+h*0.52)
        path.cubicTo(x+w*0.92, y+h*0.78, cx+w*0.30, y+h*0.92, cx, y+h)
        path.cubicTo(cx-w*0.30, y+h*0.92, x+w*0.08, y+h*0.78, x+w*0.08, y+h*0.52)
        path.lineTo(x+w*0.08, y+h*0.10)
        path.closeSubpath()
        return path

    def _jersey_path(self,box):
        x,y,w,h=box.x(),box.y(),box.width(),box.height()
        cx=x+w/2.0
        path=QPainterPath()
        path.moveTo(cx-w*0.20, y)                    # épaule gauche
        path.lineTo(cx-w*0.46, y+h*0.09)             # haut manche
        path.lineTo(cx-w*0.60, y+h*0.38)             # bas manche
        path.lineTo(cx-w*0.40, y+h*0.46)
        path.lineTo(cx-w*0.30, y+h*0.30)             # aisselle
        path.lineTo(cx-w*0.27, y+h*0.96)             # flanc gauche
        path.lineTo(cx+w*0.27, y+h*0.96)
        path.lineTo(cx+w*0.30, y+h*0.30)
        path.lineTo(cx+w*0.40, y+h*0.46)
        path.lineTo(cx+w*0.60, y+h*0.38)
        path.lineTo(cx+w*0.46, y+h*0.09)
        path.lineTo(cx+w*0.20, y)
        path.lineTo(cx+w*0.09, y+h*0.08)             # encolure
        path.quadTo(cx, y+h*0.17, cx-w*0.09, y+h*0.08)
        path.closeSubpath()
        return path

    def paintEvent(self,event):
        import math
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        outer=QRectF(self.rect()).adjusted(4,4,-4,-4)
        if outer.width()<40 or outer.height()<40:
            p.end(); return
        # ---- fond "stade" : dégradé club + halo + lignes de terrain
        bg=QLinearGradient(outer.topLeft(),outer.bottomLeft())
        top=QColor(self.primary).darker(255); top.setAlpha(235)
        bot=QColor(self.secondary).darker(150); bot.setAlpha(245)
        bg.setColorAt(0.0,QColor("#0a1522")); bg.setColorAt(0.45,top); bg.setColorAt(1.0,bot)
        p.setPen(QPen(QColor("#2d4058"),1)); p.setBrush(bg)
        p.drawRoundedRect(outer,16,16)
        # halo derrière les objets
        halo=QRadialGradient(outer.center(),outer.width()*0.55)
        hc=QColor(self.primary); hc.setAlpha(70)
        halo.setColorAt(0.0,hc); halo.setColorAt(1.0,QColor(0,0,0,0))
        p.setPen(Qt.NoPen); p.setBrush(halo)
        p.drawRoundedRect(outer.adjusted(2,2,-2,-2),15,15)
        # lignes de terrain très discrètes
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(255,255,255,14),1))
        p.drawEllipse(QPointF(outer.center().x(),outer.center().y()),outer.height()*0.42,outer.height()*0.42)
        p.drawLine(QPointF(outer.left()+10,outer.center().y()),QPointF(outer.right()-10,outer.center().y()))
        # ---- zone de dessin 16:9 centrée
        name_h=max(24,outer.height()*0.13)
        zone=QRectF(outer.left()+12,outer.top()+10,outer.width()-24,outer.height()-20-name_h)
        scale=min(zone.width()/self.RATIO_W,zone.height()/self.RATIO_H)
        bw=self.RATIO_W*scale; bh=self.RATIO_H*scale
        bx=zone.left()+(zone.width()-bw)/2.0; by=zone.top()+(zone.height()-bh)/2.0
        cy=by+bh*0.47
        primary=QColor(self.primary); secondary=QColor(self.secondary)
        # ---- ÉCUSSON (gauche) -------------------------------------------------
        cw=bh*0.36; ch=cw*1.20
        crest_box=QRectF(bx+bw*0.31-cw/2, cy-ch/2, cw, ch)
        initials="".join(part[0] for part in self.club_name.split()[:2]).upper() or "FC"
        paint_crest(p,crest_box,self.primary,self.secondary,initials[:3],self.logo)
        # ---- MAILLOT (droite) : même moteur que les vignettes du jeu -------
        jw=bh*0.54; jh=bh*0.64
        jbox=QRectF(bx+bw*0.70-jw/2, cy-jh/2, jw, jh)
        shadow=QRadialGradient(QPointF(jbox.center().x(),jbox.bottom()+jh*0.06),jw*0.55)
        shadow.setColorAt(0.0,QColor(0,0,0,120)); shadow.setColorAt(1.0,QColor(0,0,0,0))
        p.setPen(Qt.NoPen); p.setBrush(shadow)
        p.drawEllipse(QPointF(jbox.center().x(),jbox.bottom()+jh*0.05),jw*0.55,jh*0.10)
        paint_kit(p,jbox,self.primary,self.secondary,self.kit,border=True,number="9")
        # ---- plaque de nom ----------------------------------------------------
        plate=QRectF(outer.left()+16,outer.bottom()-name_h-4,outer.width()-32,name_h-2)
        pp=QColor("#0a121d"); pp.setAlpha(205)
        p.setPen(QPen(QColor(255,255,255,26),1)); p.setBrush(pp); p.drawRoundedRect(plate,9,9)
        # pastilles de couleurs
        dot=plate.height()*0.42
        p.setPen(Qt.NoPen); p.setBrush(primary)
        p.drawEllipse(QPointF(plate.left()+dot*0.9,plate.center().y()),dot*0.5,dot*0.5)
        p.setBrush(secondary)
        p.drawEllipse(QPointF(plate.left()+dot*2.0,plate.center().y()),dot*0.5,dot*0.5)
        nf=QFont("Segoe UI"); nf.setPixelSize(max(9,int(plate.height()*0.46))); nf.setBold(True)
        p.setFont(nf); p.setPen(QColor("#f2f7ff"))
        p.drawText(plate.adjusted(dot*3.0,0,-10,0),Qt.AlignVCenter|Qt.AlignLeft,self.club_name[:30].upper())
        p.end()


class PlayerRadar(QWidget):
    """Radar FM-like compact pour visualiser les six attributs principaux."""
    def __init__(self,parent=None):
        super().__init__(parent); self.values=[0]*6; self.labels=["TEC","PAS","FIN","DÉF","END","GARD"]; self.setMinimumSize(210,190)
    def set_values(self,values): self.values=[max(0,min(100,float(v or 0))) for v in values[:6]]; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); r=QRectF(self.rect()); cx=r.center().x(); cy=r.center().y(); radius=min(r.width(),r.height())*.31
        p.setPen(QPen(QColor("#354761"),1)); p.setBrush(Qt.NoBrush)
        points=[]
        import math
        for ring in (1,.75,.5,.25):
            poly=QPolygonF()
            for i in range(6):
                a=-math.pi/2+i*math.pi/3; poly.append(QPointF(cx+math.cos(a)*radius*ring,cy+math.sin(a)*radius*ring))
            p.drawPolygon(poly)
        for i,label in enumerate(self.labels):
            a=-math.pi/2+i*math.pi/3; end=QPointF(cx+math.cos(a)*radius,cy+math.sin(a)*radius); p.drawLine(QPointF(cx,cy),end)
            tx=cx+math.cos(a)*(radius+18); ty=cy+math.sin(a)*(radius+18); p.setPen(QColor("#9fb0c8")); p.setFont(QFont("Segoe UI",7,QFont.Bold)); p.drawText(QRectF(tx-24,ty-8,48,16),Qt.AlignCenter,label)
        poly=QPolygonF()
        for i,value in enumerate(self.values):
            a=-math.pi/2+i*math.pi/3; poly.append(QPointF(cx+math.cos(a)*radius*value/100,cy+math.sin(a)*radius*value/100))
        p.setPen(QPen(QColor("#65d9aa"),2)); p.setBrush(QColor(76,210,161,75)); p.drawPolygon(poly); p.end()


class ColorNuancier(QDialog):
    """Nuancier compact pour choisir la couleur du club (remplace le dialogue système)."""

    SWATCHES = [
        "#1f8a4d", "#0d7a3f", "#2fae66", "#74c69d", "#0f4c81", "#2f6cb3", "#3fb6e8", "#4ea8de",
        "#103e8c", "#22304d", "#8c1d2c", "#b33232", "#d64545", "#a4243b", "#c47220", "#e08e12",
        "#d1495b", "#d9a83c", "#ffd166", "#6a4fb3", "#7d3fd1", "#9b5de5", "#159a9c", "#12b5cb",
        "#c33c85", "#e56db1", "#7a4a24", "#6b7a3a", "#e7edf5", "#aab4c4", "#5b6e87", "#14171f",
    ]

    def __init__(self, current, parent=None, title="Nuancier du club"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.chosen = None
        current_name = QColor(current).name() if QColor(current).isValid() else "#1f8a4d"
        root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 14); root.setSpacing(10)
        tip = QLabel("Choisis une couleur dans le nuancier"); tip.setStyleSheet("font-weight:900;color:#6bd0f2;letter-spacing:1.5px;")
        root.addWidget(tip)
        grid = QGridLayout(); grid.setSpacing(6)
        for index, color in enumerate(self.SWATCHES):
            button = QPushButton(); button.setFixedSize(38, 38)
            button.setToolTip(color.upper())
            button.setCursor(Qt.PointingHandCursor)
            if color.lower() == current_name.lower():
                button.setStyleSheet(f"QPushButton{{background:{color};border:3px solid #ffffff;border-radius:8px}}")
            else:
                button.setStyleSheet(f"QPushButton{{background:{color};border:1px solid rgba(255,255,255,60);border-radius:8px}} QPushButton:hover{{border:2px solid #6bd0f2}}")
            button.clicked.connect(lambda _=False, c=color: self._pick(c))
            grid.addWidget(button, index // 8, index % 8)
        root.addLayout(grid)
        other_row = QHBoxLayout(); other_row.addStretch()
        other = QPushButton("AUTRE COULEUR…"); other.clicked.connect(self._other_color)
        other_row.addWidget(other); root.addLayout(other_row)

    def _pick(self, color):
        self.chosen = QColor(color); self.accept()

    def _other_color(self):
        chosen = QColorDialog.getColor(QColor(self.SWATCHES[0]), self, "Couleur personnalisée")
        if chosen.isValid() and chosen.alpha() >= 255:
            self.chosen = chosen; self.accept()


class ClubSetupDialog(QDialog):
    """Création de carrière premium : formulaire aligné, palette tactile et aperçu vectoriel."""
    PALETTE = [("VERT", "#1f8a4d"), ("BLEU", "#2f6cb3"), ("ROUGE", "#b33232"),
               ("VIOLET", "#6a4fb3"), ("ORANGE", "#c47220"), ("NOIR", "#202020"),
               ("BLANC", "#e7edf5"), ("TURQUOISE", "#159a9c")]
    def __init__(self, parent=None, league_definitions=None, capacity_fn=None):
        super().__init__(parent); self.league_definitions=league_definitions or []
        self.capacity_fn=capacity_fn or (lambda level,reputation: 200+max(0,level-1)*430+reputation*8)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint); self.setWindowTitle("Nouvelle carrière")
        try:
            from PySide6.QtWidgets import QApplication as _QApp
            _scr=_QApp.primaryScreen()
            _avail=_scr.availableGeometry() if _scr else None
            _w=min(1180,(_avail.width()-30) if _avail else 1180)
            _h=min(720,(_avail.height()-40) if _avail else 720)
            self.resize(max(900,_w),max(540,_h))
        except Exception:
            self.resize(1140,700)
        self.setMinimumSize(900,520)
        root=QVBoxLayout(self); root.setContentsMargins(18,14,18,14); root.setSpacing(8)
        hero=QFrame(); hero.setObjectName("HeroPanel"); hl=QHBoxLayout(hero); hl.setContentsMargins(18,10,18,10)
        title=QLabel("NOUVELLE CARRIÈRE  •  <font color='#c7d8e8'><b>construisez une identité qui vous ressemble</b></font>"); title.setTextFormat(Qt.RichText); title.setStyleSheet("font-size:13pt;color:#f4f8fc;font-weight:900;letter-spacing:.5px;")
        hl.addWidget(title); hl.addStretch(); h=QLabel("PRÉ-SAISON  •  ÉTÉ 2026"); h.setObjectName("Muted"); hl.addWidget(h); root.addWidget(hero)
        columns=QHBoxLayout(); columns.setSpacing(16)

        # ---------- Colonne gauche : formulaire en 3 étapes ----------
        left=QFrame(); left.setObjectName("Panel"); form=QVBoxLayout(left); form.setContentsMargins(14,10,14,10); form.setSpacing(6)
        def step_title(text):
            q=QLabel(text); q.setWordWrap(True); q.setStyleSheet("font-size:8pt;font-weight:900;letter-spacing:2px;color:#6bd0f2;"); form.addWidget(q); return q
        def field_label(text):
            q=QLabel(text); q.setWordWrap(True); q.setStyleSheet("font-size:9pt;font-weight:800;letter-spacing:1px;color:#a9bfd2;"); return q
        step_title("①  PROJET DE CLUB")
        form.addWidget(field_label("NOM DU CLUB"))
        self.name_input=QLineEdit(); self.name_input.setPlaceholderText("Ex : Horizon Futsal"); self.name_input.setMinimumHeight(32); form.addWidget(self.name_input)
        form.addWidget(field_label("LIGUE DE DÉPART"))
        self.division_box=QComboBox(); self.division_box.setMinimumHeight(32)
        self.division_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.division_box.setMinimumContentsLength(14)
        for division,name,strength,budget,rep in self.league_definitions: self.division_box.addItem(f"{name}  •  niveau {7-division}/6",division)
        if self.division_box.count(): self.division_box.setCurrentIndex(min(2,self.division_box.count()-1))
        form.addWidget(self.division_box)
        self.division_description=QLabel()
        self.division_description.setWordWrap(True)
        self.division_description.setStyleSheet("background:rgba(63,182,232,22);border-left:3px solid #3fb6e8;border-radius:6px;padding:5px 8px;color:#a9c6dd;font-size:8.5pt;")
        form.addWidget(self.division_description)

        form.addWidget(field_label("DIFFICULTÉ  •  MOYENS DE DÉPART"))
        self.difficulty_box=QComboBox(); self.difficulty_box.setMinimumHeight(32)
        self.difficulty_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.difficulty_box.setMinimumContentsLength(14)
        for text,key in (("Facile  •  effectif d'expérience, budget renforcé","Facile"),
                         ("Normal  •  équilibre recommandé","Normal"),
                         ("Difficile  •  petit effectif, budget serré","Difficile")):
            self.difficulty_box.addItem(text,key)
        self.difficulty_box.setCurrentIndex(1); form.addWidget(self.difficulty_box)
        self.difficulty_description=QLabel()
        self.difficulty_description.setWordWrap(True)
        self.difficulty_description.setStyleSheet("background:rgba(200,120,60,26);border-left:3px solid #e6a341;border-radius:6px;padding:5px 8px;color:#d8c2a8;font-size:8.5pt;")
        form.addWidget(self.difficulty_description)

        step_title("②  LE MONDE  •  BASE DE DONNÉES ET ARENA")
        world=QGridLayout(); world.setHorizontalSpacing(14); world.setVerticalSpacing(6)
        world.addWidget(field_label("BASE DE DONNÉES"),0,0)
        self.database_size=QComboBox(); self.database_size.setMinimumHeight(32)
        for text,key in (("Petite base","classic"),("Base moyenne","extended"),("Grande base","large")): self.database_size.addItem(text,key)
        world.addWidget(self.database_size,1,0)
        world.addWidget(field_label("NOM DE L'ARENA"),0,1)
        self.arena_name=QLineEdit(); self.arena_name.setPlaceholderText("Ex : Arena Horizon"); self.arena_name.setMinimumHeight(32); world.addWidget(self.arena_name,1,1)
        form.addLayout(world)

        step_title("③  COULEURS DU CLUB")
        color_grid=QGridLayout(); color_grid.setHorizontalSpacing(10); color_grid.setVerticalSpacing(4)
        color_grid.addWidget(field_label("PRINCIPALE  •  MAILLOT"),0,0)
        color_grid.addWidget(field_label("SECONDAIRE  •  BANDES"),0,1)
        self.primary_color_btn=QPushButton("Choisir une couleur…")
        self.secondary_color_btn=QPushButton("Choisir une couleur…")
        color_grid.addWidget(self.primary_color_btn,1,0); color_grid.addWidget(self.secondary_color_btn,1,1)
        form.addLayout(color_grid)
        for button in (self.primary_color_btn,self.secondary_color_btn):
            button.setMinimumHeight(32); button.setMinimumWidth(0); button.setObjectName("TileButton")
        color_hint=QLabel("La principale habille le maillot ; la secondaire colore col et bandes.")
        color_hint.setObjectName("Muted"); color_hint.setWordWrap(True); form.addWidget(color_hint)

        kit_line=QHBoxLayout(); kit_line.setSpacing(8)
        kit_line.addWidget(field_label("MOTIF"))
        self.kit_row=QHBoxLayout(); self.kit_row.setSpacing(5)
        self.kit_buttons={}
        kit_styles=(("vertical","Rayures"),("horizontal","Bandes"),("diagonal","Écharpe"),
                     ("checker","Damier"),("gradient","Dégradé"))
        for key,label in kit_styles:
            b=QPushButton(label); b.setCheckable(True); b.setAutoExclusive(True)
            b.setMinimumHeight(26); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:#131c2a;border:1px solid #33415a;border-radius:8px;font-size:8pt;font-weight:800;color:#c7d2e0;padding:4px 8px;}"
                            "QPushButton:checked{background:#1f6f4a;border-color:#6ad398;color:#ffffff;}")
            b.clicked.connect(lambda _=False,k=key: self._set_kit(k))
            self.kit_buttons[key]=b; self.kit_row.addWidget(b)
        kit_line.addLayout(self.kit_row,1)
        form.addLayout(kit_line)
        self.kit_state="vertical"
        self.color1=QComboBox(); self.color2=QComboBox()
        for text,color in self.PALETTE: self.color1.addItem(text,color); self.color2.addItem(text,color)
        self.color1.setCurrentIndex(0); self.color2.setCurrentIndex(5); self.color1.setVisible(False); self.color2.setVisible(False)
        columns.addWidget(left,1)

        # ---------- Colonne droite : aperçu en direct et fiche récapitulative ----------
        right=QFrame(); right.setObjectName("Panel"); rl=QVBoxLayout(right); rl.setContentsMargins(14,12,14,12); rl.setSpacing(8)
        t=QLabel("APERÇU EN DIRECT"); t.setStyleSheet("font-weight:900;color:#6bd0f0;letter-spacing:2px;"); rl.addWidget(t)
        self.preview=ClubIdentityPreview(); self.preview.setMinimumSize(300,169); self.preview.setMaximumHeight(262); self.preview.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        rl.addWidget(self.preview,0,Qt.AlignTop)
        summary=QFrame(); summary.setObjectName("FixtureCard"); sl=QVBoxLayout(summary); sl.setContentsMargins(12,10,12,10); sl.setSpacing(3)
        self.summary_name=QLabel("VOTRE CLUB"); self.summary_name.setWordWrap(True); self.summary_name.setStyleSheet("font-size:13pt;font-weight:1000;color:#f2f6fb;letter-spacing:.5px;")
        self.summary_meta=QLabel("Ligue 3  •  pré-saison été 2026"); self.summary_meta.setWordWrap(True); self.summary_meta.setStyleSheet("font-weight:800;color:#6bd0f2;letter-spacing:.5px;")
        self.summary_details=QLabel(""); self.summary_details.setObjectName("Muted"); self.summary_details.setWordWrap(True)
        sl.addWidget(self.summary_name); sl.addWidget(self.summary_meta); sl.addWidget(self.summary_details); rl.addWidget(summary)
        rl.addStretch(1)
        hint=QLabel("Le blason, le maillot et les couleurs seront enregistrés dans votre carrière."); hint.setObjectName("Muted"); hint.setWordWrap(True); rl.addWidget(hint)
        columns.addWidget(right,1)
        columns.setStretch(0,5); columns.setStretch(1,6)
        columns_host=QWidget(); columns_host.setLayout(columns)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(columns_host); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll,1)
        buttons=QHBoxLayout(); buttons.addStretch(); cancel=QPushButton("ANNULER"); cancel.clicked.connect(self.reject); buttons.addWidget(cancel); ok=QPushButton("CRÉER LA CARRIÈRE  →"); ok.setObjectName("Primary"); ok.setMinimumWidth(190); ok.clicked.connect(self.accept); buttons.addWidget(ok); root.addLayout(buttons)
        self.color1.currentIndexChanged.connect(self.update_preview); self.color2.currentIndexChanged.connect(self.update_preview); self.name_input.textChanged.connect(self.update_preview); self.name_input.textChanged.connect(self.update_summary); self.arena_name.textChanged.connect(self.update_summary); self.division_box.currentIndexChanged.connect(self.update_division_description); self.difficulty_box.currentIndexChanged.connect(self.update_difficulty_description)
        self.primary_color_btn.clicked.connect(lambda: self._choose_color(self.color1)); self.secondary_color_btn.clicked.connect(lambda: self._choose_color(self.color2))
        self._refresh_color_buttons(); self.update_division_description(); self.update_difficulty_description(); self.update_preview()

    def update_summary(self,*_):
        if not hasattr(self,"summary_name") or not self.league_definitions: return
        division=int(self.division_box.currentData() or 3); league=self.league_definitions[division-1]
        difficulty=self.difficulty_box.currentData() or "Normal"
        budget_factor={"Facile":1.25,"Normal":1.0,"Difficile":0.72}[difficulty]
        budget=int(league[3]*.62*budget_factor); reputation=max(8,int(league[4]*.72)); capacity=self.capacity_fn(max(1,min(8,7-division)),reputation)
        self.summary_name.setText(self.name_input.text().strip().upper() or "VOTRE CLUB")
        self.summary_meta.setText(f"{league[1]}  •  {difficulty}  •  pré-saison été 2026")
        arena=self.arena_name.text().strip() or "Arena Horizon"
        self.summary_details.setText(f"Budget ≈ {budget:,} €  •  salle ≈ {capacity:,} places  •  {arena}".replace(","," "))

    def _choose_color(self, combo):
        current=QColor(combo.currentData() or "#1f8a4d")
        dialog=ColorNuancier(current, self, "Nuancier du club")
        if dialog.exec()!=QDialog.Accepted or not dialog.chosen: return
        chosen=dialog.chosen
        value=chosen.name()
        idx=combo.findData(value)
        if idx < 0:
            combo.addItem(value, value); idx=combo.count()-1
        combo.setCurrentIndex(idx); self._refresh_color_buttons(); self.update_preview()

    def _refresh_color_buttons(self):
        for button, combo, label in ((self.primary_color_btn,self.color1,"PRINCIPALE"),(self.secondary_color_btn,self.color2,"SECONDAIRE")):
            color=combo.currentData() or "#1f8a4d"
            button.setText(f"{label}  •  {color.upper()}")
            button.setStyleSheet(f"QPushButton{{background:{color};color:{'#071521' if QColor(color).lightness()>150 else '#ffffff'};font-weight:800;border:1px solid #6bd0f2;border-radius:6px;padding:6px 10px}} QPushButton:hover{{border:2px solid #ffffff}}")

    def _set_kit(self,key):
        self.kit_state=key
        self.update_preview()

    def update_preview(self):
        kit=getattr(self,"kit_state","vertical")
        btn=getattr(self,"kit_buttons",{}).get(kit)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)
        self.preview.set_state(self.color1.currentData(),self.color2.currentData(),"shield",kit,
                               self.name_input.text().strip() or "VOTRE CLUB")
        if hasattr(self,"primary_color_btn"): self._refresh_color_buttons()
    def update_division_description(self,*_):
        if not self.league_definitions: return
        division=int(self.division_box.currentData() or 3); league=self.league_definitions[division-1]
        descriptions={1:"Les clubs les plus riches et les joueurs les plus forts.",2:"Un haut niveau, des budgets confortables.",3:"Division équilibrée pour lancer un projet ambitieux.",4:"Des moyens mesurés et une progression à bâtir.",5:"Une division modeste où chaque recrutement compte.",6:"Le défi ultime : petits budgets, grands écarts de niveau."}
        budget=int(league[3]*.62); reputation=max(8,int(league[4]*.72)); capacity=self.capacity_fn(max(1,min(8,7-division)),reputation)
        self.division_description.setText(f"{league[1]} • budget {budget:,} € • salle ≈ {capacity:,} places\n{descriptions[division]}".replace(","," "))
        self.update_summary()
    def update_difficulty_description(self,*_):
        key=self.difficulty_box.currentData() or "Normal"
        descriptions={
            "Facile":"Moyens confortables : effectif déjà expérimenté (+6 de niveau), budget renforcé (+25 %), infrastructure au-dessus de la ligue. Idéal pour apprendre.",
            "Normal":"Équilibre de la ligue : effectif standard, budget standard, infrastructure normale. L'expérience de référence.",
            "Difficile":"Le vrai défi : effectif plus faible (-6 de niveau), budget réduit (-28 %), infrastructure vieillissante. Pour managers aguerris.",
        }[key]
        self.difficulty_description.setText(f"{key.upper()}  —  {descriptions}")
    def values(self):
        return {"name":self.name_input.text().strip() or "Mon Club Futsal","arena_name":self.arena_name.text().strip() or "Arena Horizon","color1":self.color1.currentData(),"color2":self.color2.currentData(),"kit_pattern":getattr(self,"kit_state","vertical"),"logo_pattern":"shield","database_size":self.database_size.currentData(),"division":int(self.division_box.currentData() or 3),"difficulty":self.difficulty_box.currentData() or "Normal"}


def _combo_chevron(color="#8fa3bd"):
    """Chevron PNG pour les listes déroulantes (cache disque)."""
    try:
        import os
        from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QColor, QPen
        from PySide6.QtCore import Qt, QPointF
        if QGuiApplication.instance() is None: return ""
        icons=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","icons")
        os.makedirs(icons,exist_ok=True)
        path=os.path.join(icons,"opt_combo_"+color.replace("#","")+".png")
        if not os.path.exists(path):
            pm=QPixmap(22,14); pm.fill(QColor(0,0,0,0))
            pp=QPainter(pm); pp.setRenderHint(QPainter.Antialiasing)
            pp.setPen(QPen(QColor(color),2.0,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            pp.drawLine(QPointF(5,5),QPointF(11,11)); pp.drawLine(QPointF(11,11),QPointF(17,5))
            pp.end(); pm.save(path,"PNG")
        return path.replace("\\","/")
    except Exception:
        return ""



_KIT_CACHE={}
_KIT_PATTERNS=("vertical","horizontal","diagonal","checker","gradient")


def kit_pattern_for(club_id, name="", explicit=None):
    """Motif stable pour un club.

    · club du joueur (id 1) : le motif choisi dans OPTIONS est respecté ;
    · clubs IA : la valeur par défaut « vertical » de la colonne est traitée
      comme « automatique », sinon TOUS les clubs porteraient le même maillot.
    Le tirage ne dépend que de l'identifiant du club : la fiche club, l'en-tête
    de match et les avatars affichent donc toujours le MÊME maillot."""
    try: cid=int(club_id or 0)
    except Exception: cid=0
    if explicit and explicit in _KIT_PATTERNS:
        if not (cid not in (0,1) and explicit=="vertical"):
            return explicit
    if cid:
        x=(cid*0x9E3779B1+0x85EBCA77)&0xFFFFFFFF
        x^=x>>16; x=(x*0x85EBCA6B)&0xFFFFFFFF; x^=x>>13; x=(x*0xC2B2AE35)&0xFFFFFFFF; x^=x>>16
        seed=x
    else:
        seed=sum((i+1)*ord(ch) for i,ch in enumerate(str(name or "club")))
    return _KIT_PATTERNS[seed % len(_KIT_PATTERNS)]


def _text_on(color):
    """Couleur de texte lisible sur un fond donné."""
    from PySide6.QtGui import QColor
    c=QColor(color)
    if not c.isValid(): return "#ffffff"
    lum=(0.299*c.red()+0.587*c.green()+0.114*c.blue())/255.0
    return "#0d1420" if lum>0.62 else "#ffffff"


def _kit_path(rect, bust=False):
    """Silhouette de maillot (ou buste pour les avatars) dans un QRectF."""
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import QPointF
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height()
    cx=x+w/2.0
    path=QPainterPath()
    if not bust:
        path.moveTo(cx-w*0.19, y+h*0.02)
        path.cubicTo(cx-w*0.32, y+h*0.02, cx-w*0.42, y+h*0.05, cx-w*0.47, y+h*0.11)
        path.lineTo(cx-w*0.60, y+h*0.25)
        path.cubicTo(cx-w*0.63, y+h*0.32, cx-w*0.59, y+h*0.37, cx-w*0.51, y+h*0.39)
        path.lineTo(cx-w*0.40, y+h*0.35)
        path.lineTo(cx-w*0.34, y+h*0.44)
        path.cubicTo(cx-w*0.36, y+h*0.64, cx-w*0.36, y+h*0.82, cx-w*0.34, y+h*0.97)
        path.lineTo(cx+w*0.34, y+h*0.97)
        path.cubicTo(cx+w*0.36, y+h*0.82, cx+w*0.36, y+h*0.64, cx+w*0.34, y+h*0.44)
        path.lineTo(cx+w*0.40, y+h*0.35)
        path.lineTo(cx+w*0.51, y+h*0.39)
        path.cubicTo(cx+w*0.59, y+h*0.37, cx+w*0.63, y+h*0.32, cx+w*0.60, y+h*0.25)
        path.lineTo(cx+w*0.47, y+h*0.10)
        path.cubicTo(cx+w*0.42, y+h*0.05, cx+w*0.32, y+h*0.02, cx+w*0.19, y+h*0.02)
        path.lineTo(cx+w*0.09, y+h*0.06)
        path.cubicTo(cx+w*0.04, y+h*0.12, cx-w*0.04, y+h*0.12, cx-w*0.09, y+h*0.06)
        path.closeSubpath()
    else:
        path.moveTo(cx-w*0.20, y)
        path.cubicTo(cx-w*0.34, y+h*0.02, cx-w*0.46, y+h*0.10, cx-w*0.50, y+h*0.22)
        path.lineTo(cx-w*0.50, y+h*0.58)
        path.lineTo(cx-w*0.33, y+h*0.62)
        path.lineTo(cx-w*0.30, y+h*0.40)
        path.lineTo(cx-w*0.30, y+h*1.06)
        path.lineTo(cx+w*0.30, y+h*1.06)
        path.lineTo(cx+w*0.30, y+h*0.40)
        path.lineTo(cx+w*0.33, y+h*0.62)
        path.lineTo(cx+w*0.50, y+h*0.58)
        path.lineTo(cx+w*0.50, y+h*0.22)
        path.cubicTo(cx+w*0.46, y+h*0.10, cx+w*0.34, y+h*0.02, cx+w*0.20, y)
        path.lineTo(cx+w*0.10, y+h*0.03)
        path.cubicTo(cx+w*0.05, y+h*0.12, cx-w*0.05, y+h*0.12, cx-w*0.10, y+h*0.03)
        path.closeSubpath()
    return path


def paint_kit(painter, rect, primary="#1f8a4d", secondary="#0f3d27", pattern="vertical",
              border=True, bust=False, number=None, number_color=None):
    """Dessine un maillot complet (corps + motifs + col + poignets + ombrage).

    `bust=True` cadre le buste pour les avatars ; `number` ajoute le dossard."""
    from PySide6.QtGui import QColor, QPen, QBrush, QLinearGradient, QFont, QPolygonF
    from PySide6.QtCore import Qt, QRectF, QPointF
    prim=QColor(primary if QColor(primary).isValid() else "#1f8a4d")
    sec=QColor(secondary if QColor(secondary).isValid() else prim.darker(170))
    path=_kit_path(rect,bust)
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height()
    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    # Base : dégradé vertical doux (tissu éclairé en haut)
    base=QLinearGradient(QPointF(x,y),QPointF(x,y+h))
    base.setColorAt(0.0,prim.lighter(112)); base.setColorAt(0.55,prim); base.setColorAt(1.0,prim.darker(112))
    painter.setPen(Qt.NoPen); painter.setBrush(QBrush(base)); painter.drawPath(path)
    # Motifs, découpés dans le vêtement
    painter.save(); painter.setClipPath(path)
    if pattern=="vertical":
        bands=5
        for k in range(bands):
            if k%2==0: continue
            painter.setBrush(sec); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x+w*(k/bands),y,w/bands+0.5,h))
    elif pattern in ("horizontal","hoops"):
        bands=4
        for k in range(bands):
            if k%2==1: continue
            painter.setBrush(sec); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x,y+h*(k/bands),w,h/bands+0.5))
    elif pattern in ("diagonal","sash"):
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(sec,max(2.0,w*0.16),Qt.SolidLine,Qt.FlatCap))
        painter.drawLine(QPointF(x-w*0.10,y+h*0.92),QPointF(x+w*1.10,y+h*0.12))
    elif pattern=="checker":
        painter.setPen(Qt.NoPen); painter.setBrush(sec)
        cell=w/6.0
        for ix in range(-1,8):
            for iy in range(-1,8):
                if (ix+iy)%2==0:
                    painter.drawRect(QRectF(x+ix*cell,y+iy*cell,cell,cell))
    elif pattern=="gradient":
        g=QLinearGradient(QPointF(x,y),QPointF(x,y+h))
        g.setColorAt(0.0,prim.lighter(130)); g.setColorAt(1.0,sec)
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(g)); painter.drawPath(path)
    # OMBRAGE : reflet d'épaule à gauche, ombre sur les flancs et le bas
    sheen=QLinearGradient(QPointF(x+w*0.10,y),QPointF(x+w*0.62,y+h*0.85))
    sheen.setColorAt(0.0,QColor(255,255,255,58)); sheen.setColorAt(0.55,QColor(255,255,255,0))
    painter.setPen(Qt.NoPen); painter.setBrush(QBrush(sheen)); painter.drawPath(path)
    side=QLinearGradient(QPointF(x,y),QPointF(x+w,y))
    side.setColorAt(0.0,QColor(0,0,0,66)); side.setColorAt(0.18,QColor(0,0,0,0))
    side.setColorAt(0.82,QColor(0,0,0,0)); side.setColorAt(1.0,QColor(0,0,0,66))
    painter.setBrush(QBrush(side)); painter.drawPath(path)
    bottom=QLinearGradient(QPointF(x,y+h*0.55),QPointF(x,y+h))
    bottom.setColorAt(0.0,QColor(0,0,0,0)); bottom.setColorAt(1.0,QColor(0,0,0,70))
    painter.setBrush(QBrush(bottom)); painter.drawPath(path)
    painter.restore()
    # COL et POIGNETS
    trim=sec.darker(112)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(trim,max(1.4,w*0.045),Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if bust:
        painter.setPen(QPen(trim.darker(145),max(1.3,w*0.032),Qt.SolidLine,Qt.RoundCap))
        painter.drawArc(QRectF(x+w/2.0-w*0.13,y+h*0.002,w*0.26,h*0.15),205*16,130*16)
    else:
        coll=QPolygonF([QPointF(x+w/2.0-w*0.09,y+h*0.085),
                        QPointF(x+w/2.0,y+h*0.185),
                        QPointF(x+w/2.0+w*0.09,y+h*0.085)])
        painter.drawPolyline(coll)
    cuff_y=y+(h*0.55 if bust else h*0.34)
    painter.setPen(QPen(trim,max(1.2,w*0.035),Qt.SolidLine,Qt.RoundCap))
    painter.drawLine(QPointF(x+w*0.06,cuff_y+h*0.03),QPointF(x+w*0.17,cuff_y-h*0.01))
    painter.drawLine(QPointF(x+w*0.94,cuff_y+h*0.03),QPointF(x+w*0.83,cuff_y-h*0.01))
    # CONTOUR
    if border:
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255,255,255,170),max(1.0,w*0.014)))
        painter.drawPath(path)
    # NUMERO
    if number:
        from PySide6.QtGui import QPainterPath
        painter.save(); painter.setClipPath(path)
        fnt=QFont("Segoe UI", max(6, int(h*(0.26 if len(str(number))<=2 else 0.18))), QFont.Black)
        painter.setFont(fnt)
        nrect=QRectF(x+w*0.16,y+h*(0.30 if bust else 0.32),w*0.68,h*0.56)
        txt=str(number)
        # contour contrasté : indispensable sur damier / rayures claires
        base_col=QColor(number_color) if number_color else QColor(_text_on(prim))
        outline=QColor(0,0,0,205) if _crest_lum(base_col)>0.55 else QColor(255,255,255,215)
        fm=painter.fontMetrics()
        tw=fm.horizontalAdvance(txt); asc=fm.ascent(); desc=fm.descent()
        bx=nrect.center().x()-tw/2.0
        by=nrect.center().y()+(asc-desc)/2.0
        tpath=QPainterPath(); tpath.addText(QPointF(bx,by),fnt,txt)
        # ombre
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(0,0,0,110))
        painter.save(); painter.translate(max(1.0,h*0.012),max(1.0,h*0.02)); painter.drawPath(tpath); painter.restore()
        # liseré
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(outline,max(1.6,h*0.038),Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        painter.drawPath(tpath)
        # lettres
        painter.setPen(Qt.NoPen); painter.setBrush(base_col); painter.drawPath(tpath)
        painter.restore()
    painter.restore()


def _crest_shape(rect, pattern="shield"):
    """Silhouette d'écusson : bouclier, rond, losange ou carré moderne."""
    from PySide6.QtGui import QPainterPath
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height()
    cx=x+w/2.0
    path=QPainterPath()
    if pattern in ("round","monogram"):
        path.addEllipse(rect)
    elif pattern=="diamond":
        path.moveTo(cx,y+h*0.02); path.lineTo(x+w*0.97,y+h*0.50)
        path.lineTo(cx,y+h*0.98); path.lineTo(x+w*0.03,y+h*0.50)
        path.closeSubpath()
    elif pattern=="modern":
        path.addRoundedRect(rect,w*0.20,w*0.20)
    else:
        path.moveTo(cx,y+h*0.97)
        path.cubicTo(x+w*0.24,y+h*0.82, x+w*0.055,y+h*0.66, x+w*0.055,y+h*0.34)
        path.lineTo(x+w*0.055,y+h*0.13)
        path.quadTo(x+w*0.055,y+h*0.065, x+w*0.135,y+h*0.065)
        path.lineTo(x+w*0.865,y+h*0.065)
        path.quadTo(x+w*0.945,y+h*0.065, x+w*0.945,y+h*0.13)
        path.lineTo(x+w*0.945,y+h*0.34)
        path.cubicTo(x+w*0.945,y+h*0.66, x+w*0.76,y+h*0.82, cx,y+h*0.97)
        path.closeSubpath()
    return path


def _crest_lum(color):
    from PySide6.QtGui import QColor
    c=QColor(color)
    if not c.isValid(): return 0.0
    return (0.299*c.red()+0.587*c.green()+0.114*c.blue())/255.0


def paint_crest(painter, rect, bg1="#2f6b4c", bg2="#18492f", initials="", pattern="shield", shadow=True):
    """Blason premium : ombre, émail en dégradé, reflet, médaillon central,
    anneau métallique et monogramme contrasté."""
    from PySide6.QtGui import QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath, QFont
    from PySide6.QtCore import Qt, QPointF
    c1=QColor(bg1 if QColor(bg1).isValid() else "#2f6b4c")
    c2=QColor(bg2 if QColor(bg2).isValid() else c1.darker(165).name())
    path=_crest_shape(rect,pattern)
    # Ombre portée
    if shadow:
        painter.save(); painter.translate(rect.width()*0.02,rect.height()*0.042)
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(0,0,0,105))
        painter.drawPath(path); painter.restore()
    # Émail : dégradé vertical + bande basse plus dense
    grad=QLinearGradient(rect.topLeft(),rect.bottomLeft())
    grad.setColorAt(0.0,c1.lighter(128)); grad.setColorAt(0.50,c1); grad.setColorAt(1.0,c2)
    painter.setPen(Qt.NoPen); painter.setBrush(grad); painter.drawPath(path)
    painter.save(); painter.setClipPath(path)
    lower=QLinearGradient(0,rect.top()+rect.height()*0.50,0,rect.bottom())
    band=QColor(c2); band.setAlpha(190)
    lower.setColorAt(0.0,QColor(band.red(),band.green(),band.blue(),0)); lower.setColorAt(1.0,band)
    painter.setBrush(lower); painter.drawRect(rect)
    # reflet diagonal
    shine=QLinearGradient(rect.topLeft(),QPointF(rect.left()+rect.width()*0.88,rect.top()+rect.height()))
    shine.setColorAt(0.0,QColor(255,255,255,86)); shine.setColorAt(0.42,QColor(255,255,255,14))
    shine.setColorAt(1.0,QColor(255,255,255,0))
    painter.setBrush(shine); painter.drawRect(rect)
    # halo du haut (relief bombé)
    halo=QRadialGradient(QPointF(rect.center().x(),rect.top()+rect.height()*0.08),rect.width()*0.62)
    halo.setColorAt(0.0,QColor(255,255,255,64)); halo.setColorAt(1.0,QColor(255,255,255,0))
    painter.setBrush(halo); painter.drawRect(rect)
    painter.restore()
    # MÉDAILLON central derrière les initiales (clair sur écusson clair)
    _light=_crest_lum(c1)>0.60
    if initials:
        cx,cy=rect.center().x(),rect.center().y()+rect.height()*0.03
        pr=min(rect.width(),rect.height())*0.30
        plate=QRadialGradient(QPointF(cx,cy-pr*0.45),pr*1.35)
        if _light:
            plate.setColorAt(0.0,QColor(255,255,255,165)); plate.setColorAt(0.65,QColor(255,255,255,110))
            plate.setColorAt(1.0,QColor(255,255,255,55))
            edge=QColor(0,0,0,42)
        else:
            plate.setColorAt(0.0,QColor(255,255,255,38)); plate.setColorAt(0.65,QColor(0,0,0,38))
            plate.setColorAt(1.0,QColor(0,0,0,92))
            edge=QColor(255,255,255,58)
        painter.setPen(QPen(edge,max(1.0,rect.width()*0.012)))
        painter.setBrush(plate); painter.drawEllipse(QPointF(cx,cy),pr,pr)
    # Liseré intérieur
    inner=_crest_shape(rect.adjusted(rect.width()*0.085,rect.height()*0.075,
                                     -rect.width()*0.085,-rect.height()*0.075),pattern)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255,255,255,76),max(1.0,rect.width()*0.016)))
    painter.drawPath(inner)
    # Anneau extérieur MÉTALLIQUE (dégradé argent)
    rim=QLinearGradient(rect.topLeft(),rect.bottomRight())
    rim.setColorAt(0.0,QColor("#ffffff")); rim.setColorAt(0.38,QColor("#e9eff9"))
    rim.setColorAt(0.62,QColor("#aebdd2")); rim.setColorAt(1.0,QColor("#f6faff"))
    painter.setPen(QPen(QBrush(rim),max(1.4,rect.width()*0.032)))
    painter.drawPath(path)
    painter.setPen(QPen(QColor(0,0,0,80),max(1.0,rect.width()*0.010)))
    painter.drawPath(_crest_shape(rect.adjusted(rect.width()*0.020,rect.height()*0.018,
                                                -rect.width()*0.020,-rect.height()*0.018),pattern))
    # Bande diagonale du blason « monogramme »
    if pattern=="monogram":
        painter.save(); painter.setClipPath(path)
        painter.setPen(QPen(QColor(255,255,255,62),max(1.0,rect.width()*0.055)))
        painter.drawLine(QPointF(rect.left()+rect.width()*0.16,rect.bottom()-rect.height()*0.16),
                         QPointF(rect.right()-rect.width()*0.16,rect.top()+rect.height()*0.16))
        painter.restore()
    # Monogramme
    if initials:
        light=_light
        txt=QColor("#0b1220") if light else QColor("#ffffff")
        halo_c=QColor(255,255,255,200) if light else QColor(0,0,0,160)
        font=QFont("Segoe UI Black"); font.setPixelSize(max(7,int(rect.height()*0.29))); font.setBold(True)
        painter.setFont(font)
        fm=painter.fontMetrics()
        tw=fm.horizontalAdvance(initials)
        asc=fm.ascent(); desc=fm.descent()
        base=rect.center().y()+(asc-desc)/2.0+rect.height()*0.045
        x=rect.center().x()-tw/2.0
        painter.setPen(QColor(0,0,0,130))
        painter.drawText(QPointF(x+rect.width()*0.012,base+rect.height()*0.024),initials)
        tp=QPainterPath(); tp.addText(QPointF(x,base),font,initials)
        painter.setBrush(Qt.NoBrush); painter.setPen(QPen(halo_c,max(1.0,rect.width()*0.026)))
        painter.drawPath(tp)
        painter.setPen(Qt.NoPen); painter.setBrush(txt); painter.drawPath(tp)


def kit_pixmap(primary="#1f8a4d", secondary="#0f3d27", pattern="vertical", size=64,
               bg=None, border=True):
    """Vignette de maillot aux couleurs du club, mise en cache."""
    key=("v2",str(primary),str(secondary),str(pattern),int(size),str(bg),bool(border))
    hit=_KIT_CACHE.get(key)
    if hit is not None: return hit
    from PySide6.QtGui import QPixmap, QPainter, QColor
    from PySide6.QtCore import Qt, QRectF
    w=h=int(size); pm=QPixmap(w,h); pm.fill(Qt.transparent)
    p=QPainter(pm)
    try:
        if bg:
            bgc=QColor(bg); bgc.setAlpha(160)
            p.setPen(Qt.NoPen); p.setBrush(bgc)
            p.drawRoundedRect(QRectF(0,0,w,h),w*0.18,w*0.18)
        m=w*0.075
        paint_kit(p,QRectF(m,m*0.9,w-2*m,h-2*m*0.9),primary,secondary,pattern,border=border,bust=False)
    finally:
        p.end()
    if len(_KIT_CACHE)>400: _KIT_CACHE.clear()
    _KIT_CACHE[key]=pm
    return pm


def menu_bars_pixmap(size=40,color="#aebbd0"):
    """Trois barres horizontales dessinées (aucune dépendance aux polices)."""
    from PySide6.QtGui import QPixmap, QPainter, QColor, QPen
    from PySide6.QtCore import Qt as _Qt, QPointF as _QP
    pm=QPixmap(size,size); pm.fill(_Qt.transparent)
    p=QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        stroke=max(1.6,size*0.085)
        p.setPen(QPen(QColor(color),stroke,_Qt.SolidLine,_Qt.RoundCap))
        c=size/2.0+(0.5 if size%2==0 else 0.0)
        r=size*0.33
        for y in (-r*0.62,0.0,r*0.62):
            p.drawLine(_QP(c-r*0.86,c+y),_QP(c+r*0.86,c+y))
    finally:
        p.end()
    return pm


class MessageListDelegate(QStyledItemDelegate):
    """Cartes de courrier dessinées : expéditeur, aperçu, date et état lisible."""

    ROLE_ID = Qt.UserRole
    ROLE_TITLE = Qt.UserRole + 1
    ROLE_PREVIEW = Qt.UserRole + 2
    ROLE_DATE = Qt.UserRole + 3
    ROLE_STATUS = Qt.UserRole + 4
    ROLE_UNREAD = Qt.UserRole + 5
    ROLE_COLOR = Qt.UserRole + 6
    ROLE_BADGE = Qt.UserRole + 7
    ROLE_KIND = Qt.UserRole + 8

    ROLE_SENDER = Qt.UserRole + 9
    ROLE_INITIALS = Qt.UserRole + 10

    def sizeHint(self, option, index):
        return QSize(360, 76)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = option.rect.adjusted(2, 1, -2, -1)
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        unread = bool(index.data(self.ROLE_UNREAD))
        color = QColor(index.data(self.ROLE_COLOR) or "#7f93ad")
        if not color.isValid():
            color = QColor("#7f93ad")

        if selected:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#1b2c43"))
            painter.drawRoundedRect(rect, 8, 8)
        elif hover:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#121f2f"))
            painter.drawRoundedRect(rect, 8, 8)
        else:
            painter.setPen(QPen(QColor("#172635"), 1))
            painter.drawLine(rect.left() + 10, rect.bottom(), rect.right() - 10, rect.bottom())

        if unread:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#7fc7e8"))
            painter.drawRoundedRect(QRectF(rect.left(), rect.top() + 12, 3, rect.height() - 24), 2, 2)

        # Avatar rond avec initiales de l'expéditeur.
        avatar = QRectF(rect.left() + 11, rect.center().y() - 16, 32, 32)
        fill = QColor(color); fill.setAlpha(48)
        edge = QColor(color); edge.setAlpha(150)
        painter.setPen(QPen(edge, 1)); painter.setBrush(fill)
        painter.drawEllipse(avatar)
        initials = str(index.data(self.ROLE_INITIALS) or index.data(self.ROLE_BADGE) or "•")
        f = QFont("Segoe UI", 7); f.setBold(True); f.setWeight(QFont.Black)
        painter.setFont(f); painter.setPen(QColor("#eaf2fb"))
        painter.drawText(avatar, int(Qt.AlignCenter), initials[:2])

        text_left = avatar.right() + 11
        text_right = rect.right() - 12
        date_text = str(index.data(self.ROLE_DATE) or "")
        status = str(index.data(self.ROLE_STATUS) or "done")
        tone = {"ready": QColor("#d9b46a"), "waiting": QColor("#7fb2d8"),
                "report": QColor("#a99bd0"), "rival": QColor("#ff9daa"),
                "accepted": QColor("#7de0aa"), "closed": QColor("#8ea3bd")}.get(status)

        f = QFont("Segoe UI", 6.5); f.setBold(True)
        painter.setFont(f); painter.setPen(QColor("#7288a1"))
        date_w = 68
        painter.drawText(QRectF(rect.right() - 12 - date_w, rect.top() + 8, date_w, 14),
                         int(Qt.AlignRight | Qt.AlignVCenter), date_text)
        if tone is not None:
            painter.setPen(Qt.NoPen); painter.setBrush(tone)
            painter.drawEllipse(QRectF(rect.right() - 17, rect.top() + 26, 6, 6))
        sender_right = text_right - (date_w + 12)

        sender = str(index.data(self.ROLE_SENDER) or "")
        f = QFont("Segoe UI", 8); f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor("#f3f8fd") if unread else QColor("#cbd8e7"))
        fm = QFontMetrics(f)
        painter.drawText(QRectF(text_left, rect.top() + 7, max(10, sender_right - text_left), 15),
                         int(Qt.AlignLeft | Qt.AlignVCenter),
                         fm.elidedText(sender, Qt.ElideRight, int(max(10, sender_right - text_left))))

        title = str(index.data(self.ROLE_TITLE) or "")
        f = QFont("Segoe UI", 7.5); f.setBold(unread)
        painter.setFont(f); painter.setPen(QColor("#e6eef8") if unread else QColor("#b6c6d9"))
        fm = QFontMetrics(f)
        painter.drawText(QRectF(text_left, rect.top() + 26, max(10, text_right - text_left), 15),
                         int(Qt.AlignLeft | Qt.AlignVCenter),
                         fm.elidedText(title, Qt.ElideRight, int(max(10, text_right - text_left))))

        preview = str(index.data(self.ROLE_PREVIEW) or "")
        f = QFont("Segoe UI", 7); f.setBold(False)
        painter.setFont(f); painter.setPen(QColor("#7f93ad"))
        fm = QFontMetrics(f)
        painter.drawText(QRectF(text_left, rect.top() + 44, max(10, text_right - text_left), 14),
                         int(Qt.AlignLeft | Qt.AlignVCenter),
                         fm.elidedText(preview, Qt.ElideRight, int(max(10, text_right - text_left))))
        painter.restore()


class HelpPanel(QWidget):
    """Aide interactive : sommaire par thème, recherche et navigation par liens."""

    THEME_COLORS = {
        "demarrage": "#7fb7a6",
        "direction": "#8b9fc7",
        "effectif": "#c2a979",
        "tactiques": "#9db3d4",
        "entrainement": "#8fb9a6",
        "mercato": "#b39ac9",
        "finances": "#a9c08a",
        "competitions": "#c9a99a",
        "interface": "#8fa4bf",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = ""
        self._topic_hay = {}
        for topic in HELP_TOPICS:
            plain = re.sub(r"<[^>]+>", " ", str(topic.get("html", "")))
            theme = THEME_INDEX.get(topic.get("theme", ""), ("", ""))[0]
            self._topic_hay[topic["id"]] = self._norm(" ".join((
                topic.get("title", ""), topic.get("keywords", ""), theme, plain)))
        self.setStyleSheet("""
            QFrame#HelpHero { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #142236,stop:0.6 #111d2e,stop:1 #0d1725);
                border:1px solid #2c405c; border-radius:13px; }
            QLabel#HelpTitle { font-size:13pt; font-weight:1000; color:#f2f7fd; letter-spacing:.7px; }
            QLabel#HelpKicker { font-size:7pt; font-weight:900; color:#8fa4bf; letter-spacing:1.6px; }
            QFrame#HelpNav { background:#0c1622; border:1px solid #22344a; border-radius:11px; }
            QLineEdit#HelpSearch { background:#0d1826; border:1px solid #2b3d55; border-radius:9px;
                color:#e9f0f8; padding:7px 10px; font-weight:700; }
            QLineEdit#HelpSearch:hover { border-color:#3f5b7c; }
            QLineEdit#HelpSearch:focus { border-color:#5a7d9e; background:#0f1c2c; }
            QTreeWidget#HelpTree { background:transparent; border:0; color:#b6c6da; outline:0;
                font-size:8.5pt; }
            QTreeWidget#HelpTree::item { padding:4px 6px; border-radius:6px; margin:1px 0; }
            QTreeWidget#HelpTree::item:hover { background:#132135; color:#e7eef7; }
            QTreeWidget#HelpTree::item:selected { background:#1b2c42; color:#ffffff; }
            QTreeWidget#HelpTree::branch { background:transparent; }
            QLabel#HelpCount { color:#7488a2; font-size:7pt; font-weight:800; }
            QPushButton#HelpSummary { background:#121e2e; border:1px solid #2b3d55; border-radius:8px;
                color:#bed0e5; font-size:7.5pt; font-weight:900; padding:7px 10px; letter-spacing:.5px; }
            QPushButton#HelpSummary:hover { background:#1a2a40; border-color:#45617f; color:#f1f6fb; }
            QTextBrowser#HelpView { background:#0c1622; border:1px solid #22344a; border-radius:11px;
                padding:0; selection-background-color:#2a4760; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(10)

        # ---------------- EN-TÊTE : identité + recherche ----------------
        hero = QFrame(); hero.setObjectName("HelpHero")
        hh = QHBoxLayout(hero); hh.setContentsMargins(14, 10, 14, 10); hh.setSpacing(12)
        mark = QLabel(); mark.setFixedSize(44, 44); mark.setAlignment(Qt.AlignCenter)
        mark.setPixmap(self._glyph(24, "#dbe9f7"))
        mark.setStyleSheet("background:#182538;border:1px solid #3b5675;border-radius:12px;")
        hh.addWidget(mark)
        head_col = QVBoxLayout(); head_col.setSpacing(1)
        title = QLabel("CENTRE D'AIDE"); title.setObjectName("HelpTitle")
        subtitle = QLabel("Réponses rapides, recherche instantanée.")
        subtitle.setObjectName("Muted")
        head_col.addWidget(title); head_col.addWidget(subtitle)
        hh.addLayout(head_col, 1)
        self.search = QLineEdit(); self.search.setObjectName("HelpSearch")
        self.search.setPlaceholderText("Rechercher : salaire, coupe, prêt…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(38)
        self.search.setMinimumWidth(240); self.search.setMaximumWidth(340)
        self.search.addAction(QIcon(self._search_glyph(15, "#8fa4bf")), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._filter)
        hh.addWidget(self.search)
        root.addWidget(hero)

        # ---------------- CORPS : sommaire + article ----------------
        body = QHBoxLayout(); body.setSpacing(10)

        nav = QFrame(); nav.setObjectName("HelpNav"); nav.setMinimumWidth(230); nav.setMaximumWidth(280)
        nl = QVBoxLayout(nav); nl.setContentsMargins(10, 10, 10, 10); nl.setSpacing(7)
        head = QHBoxLayout(); head.setSpacing(6)
        head_lbl = QLabel("THÈMES"); head_lbl.setObjectName("HelpKicker")
        head.addWidget(head_lbl); head.addStretch()
        self.count = QLabel(""); self.count.setObjectName("HelpCount")
        head.addWidget(self.count)
        nl.addLayout(head)
        self.tree = QTreeWidget(); self.tree.setObjectName("HelpTree")
        self.tree.setHeaderHidden(True); self.tree.setIndentation(12)
        self.tree.setUniformRowHeights(False); self.tree.setAnimated(True)
        self.tree.setRootIsDecorated(True); self.tree.setIconSize(QSize(11, 11))
        self.tree.setExpandsOnDoubleClick(True)
        _pal = self.tree.palette()
        _pal.setColor(QPalette.Highlight, QColor("#1f3350"))
        _pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.tree.setPalette(_pal)
        self.tree.currentItemChanged.connect(self._on_item)
        self.tree.itemClicked.connect(self._on_click)
        nl.addWidget(self.tree, 1)
        summary = QPushButton("REVENIR AU SOMMAIRE"); summary.setObjectName("HelpSummary")
        summary.setCursor(Qt.PointingHandCursor); summary.setMinimumHeight(32)
        summary.setToolTip("Revenir au sommaire complet")
        summary.clicked.connect(self._reset)
        nl.addWidget(summary)
        body.addWidget(nav)

        self.view = QTextBrowser(); self.view.setObjectName("HelpView")
        self.view.setOpenLinks(False)
        self.view.setOpenExternalLinks(False)
        self.view.anchorClicked.connect(self._on_link)
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.document().setDocumentMargin(18)
        self.view.setStyleSheet("QTextBrowser#HelpView{background:#0c1622;border:1px solid #22344a;"
                                "border-radius:11px;padding:0;}")
        body.addWidget(self.view, 1)

        root.addLayout(body, 1)

        self._populate("")
        self._select("vue-ensemble")

    # ---------------- petits dessins ----------------
    @staticmethod
    def _glyph(size=20, color="#dbe9f7"):
        """Pastille « ? » dessinée : nette à toutes les tailles."""
        pix = QPixmap(size, size); pix.fill(Qt.transparent)
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(color), max(1.3, size * 0.085), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(size * 0.10, size * 0.10, size * 0.80, size * 0.80))
            r = size * 0.20
            p.translate(size / 2.0, size / 2.0)
            path = QPainterPath()
            path.moveTo(-r * 0.62, -r * 0.34)
            path.cubicTo(-r * 0.62, -r * 1.12, r * 0.74, -r * 1.12, r * 0.74, -r * 0.22)
            path.cubicTo(r * 0.74, r * 0.18, 0.0, r * 0.02, 0.0, r * 0.58)
            p.drawPath(path)
            p.setBrush(QColor(color)); p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(-r * 0.11, r * 0.84, r * 0.22, r * 0.22))
        finally:
            p.end()
        return pix

    @staticmethod
    def _search_glyph(size=16, color="#8fa4bf"):
        """Loupe dessinée pour le champ de recherche."""
        pix = QPixmap(size, size); pix.fill(Qt.transparent)
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(color), max(1.2, size * 0.10), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(size * 0.12, size * 0.12, size * 0.50, size * 0.50))
            p.drawLine(QPointF(size * 0.58, size * 0.58), QPointF(size * 0.86, size * 0.86))
        finally:
            p.end()
        return pix

    @staticmethod
    def _dot(color, size=9):
        pix = QPixmap(size, size); pix.fill(Qt.transparent)
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen); p.setBrush(QColor(color))
            p.drawEllipse(0.5, 0.5, size - 1.0, size - 1.0)
        finally:
            p.end()
        return pix

    @staticmethod
    def _norm(text):
        value = unicodedata.normalize("NFKD", str(text or ""))
        return value.encode("ascii", "ignore").decode("ascii").lower()

    # ---------------- sommaire ----------------
    def _populate(self, query):
        self.tree.clear()
        query = self._norm(query).strip()
        shown = 0
        first = None
        terms = [term for term in query.split() if term]
        current_theme = (TOPIC_INDEX.get(self._current, {}) or {}).get("theme")
        for theme_key, theme_label, theme_desc in HELP_THEMES:
            topics = [t for t in HELP_TOPICS if t.get("theme") == theme_key]
            if terms:
                topics = [t for t in topics
                          if all(term in self._topic_hay.get(t["id"], "") for term in terms)]
            if not topics:
                continue
            top = QTreeWidgetItem([theme_label])
            top.setFlags(top.flags() & ~Qt.ItemIsSelectable)
            top.setToolTip(0, theme_desc)
            font = top.font(0); font.setBold(True); top.setFont(0, font)
            top.setForeground(0, QColor("#9fb2c8"))
            top.setIcon(0, QIcon(self._dot(self.THEME_COLORS.get(theme_key, "#8fa4bf"))))
            top.setSizeHint(0, QSize(0, 30))
            self.tree.addTopLevelItem(top)
            for topic in topics:
                item = QTreeWidgetItem([topic["title"]])
                item.setData(0, Qt.UserRole, topic["id"])
                item.setToolTip(0, topic.get("keywords", "")[:180])
                item.setSizeHint(0, QSize(0, 26))
                top.addChild(item)
                shown += 1
                if first is None:
                    first = item
            top.setExpanded(bool(terms) or theme_key == current_theme)
        if query:
            self.count.setText("%d trouvé(s)" % shown)
        else:
            self.count.setText("%d sujets" % shown)
        if first is not None:
            self.tree.setCurrentItem(first)
        elif query:
            self.count.setText("0 trouvé")
            self.view.setHtml(self._empty_html(query))

    def _empty_html(self, query):
        return ("<div align='center' style='font-family:Segoe UI;padding-top:64px;'>"
                "<div style='font-size:30pt;color:#2f4a68;font-weight:700;'>?</div>"
                "<div style='font-size:12.5pt;color:#e8eef7;font-weight:700;margin-top:12px;'>"
                "Aucun résultat</div>"
                "<p style='margin-top:10px;color:#aebfd3;'>Aucun sujet ne correspond à "
                "<b style='color:#eef4fb;'>%s</b>.</p>"
                "<p style='color:#7f93ad;font-size:9pt;'>Essaie un mot plus simple : "
                "<i>contrat, coupe, salaire, prêt, effectif, match…</i></p>"
                "</div>" % str(query))

    def _on_item(self, item, _previous=None):
        if item is None:
            return
        topic_id = item.data(0, Qt.UserRole)
        if topic_id:
            self._select(str(topic_id))

    def _on_click(self, item, _column=0):
        if item is not None and item.childCount():
            item.setExpanded(not item.isExpanded())

    def _select(self, topic_id):
        topic = TOPIC_INDEX.get(str(topic_id))
        if not topic:
            return
        self._current = topic["id"]
        # Sélection visuelle sans relancer la navigation.
        self.tree.blockSignals(True)
        for index in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(index)
            for child_index in range(top.childCount()):
                child = top.child(child_index)
                if child.data(0, Qt.UserRole) == topic["id"]:
                    top.setExpanded(True)
                    self.tree.setCurrentItem(child)
                    self.tree.scrollToItem(child)
                    break
        self.tree.blockSignals(False)
        self.view.setHtml(self._article_html(topic))

    def _article_html(self, topic):
        theme_label = THEME_INDEX.get(topic.get("theme", ""), ("Aide", ""))[0]
        body = str(topic.get("html", ""))
        return """
        <style>
          body { color:#c8d4e2; font-family:'Segoe UI'; font-size:9.5pt; }
          .theme { color:#7f94ae; font-size:7pt; font-weight:900; letter-spacing:1.6px; padding-bottom:5px; }
          h2 { color:#f3f7fc; font-size:15pt; margin:5px 0 10px 0; }
          h3 { color:#a8cbe8; font-size:10.5pt; margin:16px 0 5px 0; }
          p { margin:6px 0 8px 0; line-height:1.45; }
          ul, ol { margin:6px 0 10px 20px; }
          li { margin:4px 0; line-height:1.4; }
          b { color:#eef4fb; }
          a { color:#8fc7ea; text-decoration:none; font-weight:600; }
          .tip { background:#0f2233; border-left:3px solid #5a8fb4; padding:9px 12px;
                 margin:12px 0; color:#cfe0ee; }
          .warn { background:#241a14; border-left:3px solid #a8794f; padding:9px 12px;
                  margin:12px 0; color:#e4d3bf; }
          .see { color:#8294ad; font-size:8pt; margin-top:16px; padding-top:9px;
                 border-top:1px solid #22324a; }
          table.grid { border-collapse:collapse; width:100%%; margin:8px 0; }
          table.grid td { padding:6px 9px; border-bottom:1px solid #1d2c40; vertical-align:top; }
          table.grid td:first-child { color:#eaf1f9; width:34%%; }
        </style>
        <div class="theme">AIDE  •  %s</div>
        %s
        """ % (theme_label.upper(), body)

    def _reset(self):
        self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
        self._populate("")
        self._select("vue-ensemble")
        self.search.setFocus()

    def _filter(self, text):
        self._populate(text)
        if not str(text).strip():
            self._select(self._current or "vue-ensemble")

    def _on_link(self, url):
        target = url.toString() if hasattr(url, "toString") else str(url)
        if target.startswith("topic:"):
            self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
            self._populate("")
            self._select(target[6:])


class GameOptionsDialog(QDialog):
    """Options du jeu : presentation sobre, cartes lisibles et onglets clairs."""

    def __init__(self, options, club, parent=None, cheat_cb=None, kit_cb=None,
                 bug_cb=None):
        super().__init__(parent)
        self.setWindowTitle("Options du jeu")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setMinimumSize(820, 600)
        self.resize(900, 680)
        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0b1420,stop:1 #070d16); }
            QLabel { color:#c9d6e6; background:transparent; }
            QLabel#Muted { color:#8294ad; }
            QFrame#OptionsHero { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #121d2c,stop:1 #0d1622);
                border:1px solid #283950; border-radius:14px; }
            QFrame#OptionsSection { background:transparent; border:0; }
            QFrame#OptionRow { background:#101a27; border:1px solid #24344a; border-radius:10px; }
            QFrame#OptionRow:hover { background:#13202f; border-color:#334b67; }
            QLabel#OptionTitle { font-size:8.5pt; font-weight:900; color:#e7eef7; letter-spacing:.4px; }
            QLabel#OptionHint { font-size:8pt; color:#8294ad; }
            QLabel#SectionLabel { font-size:7.5pt; font-weight:900; color:#7f93ad; letter-spacing:1.6px; }
            QComboBox, QSpinBox { background:#0d1725; border:1px solid #2b3d55; border-radius:8px;
                padding:7px 11px; color:#eaf1fa; font-weight:700; min-height:22px; }
            QComboBox { padding-right:34px; }
            QComboBox:hover, QSpinBox:hover { border-color:#46617f; }
            QComboBox::drop-down { subcontrol-origin:padding; subcontrol-position:center right;
                width:30px; border:0; border-left:1px solid #22324a; background:transparent; }
            QComboBox::down-arrow { image:url({OPT_ARROW}); width:12px; height:8px; }
            QComboBox QAbstractItemView { background:#0e1725; color:#eaf1fa; border:1px solid #33435a;
                border-radius:9px; padding:6px; outline:0; selection-background-color:#2a4760;
                selection-color:#ffffff; }
            QComboBox QAbstractItemView::item { min-height:29px; padding:5px 9px; border-radius:6px; }
            QComboBox QAbstractItemView { background:#0e1725; alternate-background-color:#0e1725; }
            QComboBox QAbstractItemView::item { background:transparent; }
            QComboBox:on { background:#0d1725; }
            QTabBar { background:transparent; }
            QTabWidget::tab-bar { background:transparent; }
            QCheckBox { color:#dbe5f2; font-weight:700; spacing:9px; }
            QCheckBox::indicator { width:18px; height:18px; border-radius:5px; border:1px solid #3a5170; background:#0e1826; }
            QCheckBox::indicator:checked { background:#3f7d5f; border-color:#6aa887; }
            QTabWidget::pane { border:1px solid #26374d; border-radius:10px; background:#0c1622; top:-1px; }
            QTabBar::tab { background:#101a28; border:1px solid #26374d; border-bottom:none;
                border-top-left-radius:9px; border-top-right-radius:9px; color:#92a3ba; padding:8px 18px;
                font-weight:900; font-size:8.5pt; margin-right:4px; }
            QTabBar::tab:selected { background:#172438; color:#f1f5fb; border-color:#3b5675; }
            QTabBar::tab:hover { color:#dfe8f5; }
            QTextBrowser { background:#0c1622; border:1px solid #24344a; border-radius:10px; color:#c7d2e0; padding:6px; }
            QPushButton { background:#152238; color:#cfe0f5; border:1px solid #2c3d57;
                border-radius:9px; padding:8px 16px; font-weight:800; }
            QPushButton:hover { background:#1b2b45; border-color:#3f5f8a; color:#f2f7ff; }
            QPushButton#Primary { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3d5170,stop:1 #293a52);
                color:#f2f7ff; border:1px solid #5b7698; }
            QPushButton#Primary:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4a6184,stop:1 #32465f); }
            QPushButton#Ghost { background:transparent; color:#90a4bd; border:1px solid #2a3a50; padding:6px 12px; }
            QPushButton#Ghost:hover { background:#152238; color:#e4edf8; border-color:#40587a; }
            QScrollArea { background:transparent; border:0; }
            QScrollArea > QWidget > QWidget { background:transparent; }
            QScrollBar:vertical { background:#0a131e; width:10px; border-radius:5px; }
            QScrollBar::handle:vertical { background:#2b3f5c; border-radius:5px; min-height:24px; }
        """)
        _arrow = _combo_chevron("#8fa3bd")
        if _arrow:
            self.setStyleSheet(self.styleSheet().replace("{OPT_ARROW}", _arrow))

        # Finition sobre : fonds plats, bordures discretes, onglets soulignes.
        self.setStyleSheet(self.styleSheet() + """
            QDialog { background:#0a121c; }
            QFrame#OptionsHero { background:#0e1826; border:1px solid #1f2d40; border-radius:12px; }
            QFrame#OptionRow { background:#0d1724; border:1px solid #1c2a3c; border-radius:9px; }
            QFrame#OptionRow:hover { background:#101c2b; border-color:#2a3f57; }
            QLabel#SectionLabel { color:#6f849e; letter-spacing:1.4px; }
            QLabel#OptionTitle { color:#dde7f3; }
            QLabel#OptionHint { color:#7b8ea6; }
            QTabWidget::pane { border:1px solid #1c2a3c; border-radius:9px; background:#0b1521; }
            QTabBar::tab { background:transparent; border:0; border-bottom:2px solid transparent;
                color:#8298b1; padding:9px 15px; font-weight:800; font-size:8.5pt; margin-right:2px; }
            QTabBar::tab:selected { color:#eef4fb; border-bottom:2px solid #5b8fd6; }
            QTabBar::tab:hover { color:#cfe0f5; }
            QPushButton#Primary { background:#2f4a68; border:1px solid #4a6d92; color:#f2f7ff; }
            QPushButton#Primary:hover { background:#3a5779; }
            QPushButton#Ghost { border-color:#1f2d40; }
            QComboBox, QSpinBox { background:#0b1521; border:1px solid #223247; }
            QComboBox:hover, QSpinBox:hover { border-color:#3a5573; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(11)

        # ---------------- EN-TETE ----------------
        hero = QFrame(); hero.setObjectName("OptionsHero")
        hl = QHBoxLayout(hero); hl.setContentsMargins(16, 11, 12, 11); hl.setSpacing(12)
        mark = QLabel(); mark.setAlignment(Qt.AlignCenter); mark.setFixedSize(38, 38)
        mark.setPixmap(menu_bars_pixmap(21, "#cfe0f5"))
        mark.setStyleSheet("background:#141f2e;border:1px solid #2c3f56;border-radius:11px;")
        hl.addWidget(mark)
        head = QVBoxLayout(); head.setSpacing(2)
        title = QLabel("OPTIONS DU JEU")
        title.setStyleSheet("font-size:13pt;font-weight:900;color:#eef3fa;letter-spacing:.6px;")
        sub = QLabel("Apparence, messagerie, aide et coups de pouce — réglages enregistrés localement.")
        sub.setObjectName("Muted"); sub.setStyleSheet("font-size:8.5pt;color:#7f93ad;")
        head.addWidget(title); head.addWidget(sub)
        hl.addLayout(head, 1)
        close = QPushButton("FERMER"); close.setObjectName("Ghost"); close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.reject)
        hl.addWidget(close)
        root.addWidget(hero)

        def scroll_page():
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            inner = QWidget(); scroll.setWidget(inner)
            lay = QVBoxLayout(inner); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)
            return scroll, lay

        def section(lay, text):
            row = QHBoxLayout(); row.setSpacing(8)
            lab = QLabel(text); lab.setObjectName("SectionLabel")
            line = QFrame(); line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color:#22324a;background:#22324a;max-height:1px;")
            row.addWidget(lab); row.addWidget(line, 1)
            lay.addLayout(row)

        def option_row(lay, title, desc, widget):
            card = QFrame(); card.setObjectName("OptionRow")
            row = QHBoxLayout(card); row.setContentsMargins(12, 8, 12, 8); row.setSpacing(14)
            col = QVBoxLayout(); col.setSpacing(1)
            t = QLabel(title); t.setObjectName("OptionTitle")
            d = QLabel(desc); d.setObjectName("OptionHint"); d.setWordWrap(True)
            d.setMinimumWidth(0); d.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            col.addWidget(t); col.addWidget(d)
            row.addLayout(col, 1)
            widget.setMinimumWidth(210); widget.setMaximumWidth(270)
            row.addWidget(widget, 0, Qt.AlignVCenter)
            lay.addWidget(card)
            return card

        tabs = QTabWidget(); tabs.setDocumentMode(True); tabs.setObjectName("CenterTabs")
        tabs.setStyleSheet("QTabWidget::pane{border:1px solid #1c2a3c;border-radius:9px;background:#0b1521;}"
                           "QTabBar::tab{background:transparent;border:0;border-bottom:2px solid transparent;"
                           "color:#8298b1;padding:9px 15px;font-weight:800;font-size:8.5pt;margin-right:2px;}"
                           "QTabBar::tab:selected{color:#eef4fb;border-bottom:2px solid #5b8fd6;}"
                           "QTabBar::tab:hover{color:#cfe0f5;}")
        root.addWidget(tabs, 1)

        # ---------------- APPARENCE ----------------
        appearance, al = scroll_page()
        section(al, "AFFICHAGE")
        self.theme = QComboBox(); self.theme.setMinimumHeight(34)
        self.theme.addItems(["Nuit violette", "Vert futsal", "Noir & or"])
        self.theme.setCurrentText(options.get("theme", "Nuit violette"))
        self.font_size = QSpinBox(); self.font_size.setMinimumHeight(34)
        self.font_size.setRange(9, 16); self.font_size.setValue(int(options.get("font_size", 10)))
        self.font_size.setSuffix(" pt")
        self.window_mode = QComboBox(); self.window_mode.setMinimumHeight(34)
        self.window_mode.addItems(["Fenêtré", "Maximisé", "Plein écran"])
        self.window_mode.setCurrentText(options.get("window_mode", "Maximisé"))
        self.difficulty = QComboBox(); self.difficulty.setMinimumHeight(34)
        self.difficulty.addItems(["Normale", "Difficile"])
        self.difficulty.setCurrentText(options.get("difficulty", "Normale"))
        option_row(al, "THÈME DE L'INTERFACE", "Palette des écrans, des panneaux et du bandeau supérieur.", self.theme)
        option_row(al, "TAILLE DU TEXTE", "Confort de lecture : s'applique immédiatement à toute l'interface.", self.font_size)
        option_row(al, "MODE DE FENÊTRE", "Fenêtré, maximisé ou plein écran au lancement du jeu.", self.window_mode)
        option_row(al, "DIFFICULTÉ", "Difficile : board plus exigeant, IA plus agressive, revenus plus serrés.", self.difficulty)
        if kit_cb is not None:
            section(al, "IDENTITÉ DU CLUB")
            kit_box = QWidget(); kb = QHBoxLayout(kit_box); kb.setContentsMargins(0, 0, 0, 0); kb.setSpacing(5)
            cur = str(options.get("kit_pattern", "vertical") or "vertical")
            for key, label in (("vertical", "Rayures"), ("horizontal", "Bandes"), ("diagonal", "Écharpe"),
                               ("checker", "Damier"), ("gradient", "Dégradé")):
                b = QPushButton(label); b.setCheckable(True)
                b.setStyleSheet("QPushButton{background:#101a28;border:1px solid #2b3d55;border-radius:7px;"
                                "font-size:7.5pt;font-weight:800;color:#c7d2e0;padding:5px 7px;}"
                                "QPushButton:checked{background:#334a63;border-color:#5f7d9e;color:#ffffff;}")
                b.setChecked(key == cur)
                b.clicked.connect(lambda _=False, k=key: kit_cb(k))
                kb.addWidget(b)
            kb.addStretch()
            option_row(al, "MAILLOT DU CLUB", "Motif appliqué aux maillots et aux fiches joueurs.", kit_box)
        al.addStretch(1)
        tabs.addTab(appearance, "APPARENCE")

        # ---------------- MESSAGERIE ----------------
        messaging, ml = scroll_page()
        section(ml, "BRIEF DU CLUB")
        brief_card = QFrame(); brief_card.setObjectName("OptionRow")
        bl = QHBoxLayout(brief_card); bl.setContentsMargins(12, 8, 12, 8); bl.setSpacing(12)
        bcol = QVBoxLayout(); bcol.setSpacing(1)
        bt = QLabel("CADENCE DES NOUVELLES"); bt.setObjectName("OptionTitle")
        bd = QLabel("Un brief par semaine (lundi) est plus léger qu'un brief quotidien."); bd.setObjectName("OptionHint")
        bd.setWordWrap(True); bd.setMinimumWidth(0); bd.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        bcol.addWidget(bt); bcol.addWidget(bd)
        bl.addLayout(bcol, 1)
        self.brief_cadence = QComboBox(); self.brief_cadence.setMinimumWidth(210); self.brief_cadence.setMaximumWidth(270)
        self.brief_cadence.addItems(["Hebdomadaire", "Quotidien"])
        self.brief_cadence.setCurrentText(options.get("brief_cadence", "Hebdomadaire"))
        bl.addWidget(self.brief_cadence, 0, Qt.AlignVCenter)
        ml.addWidget(brief_card)

        section(ml, "MESSAGES REÇUS")
        self.msg_boxes = {}
        for key, label, tip in (
            ("msg_anniversaire", "Anniversaires des joueurs", "Reçu à chaque anniversaire d'un joueur du club — sans effet sportif (désactivé par défaut)."),
            ("msg_perf", "Performances des joueurs", "Buteurs, gardiens, jeunes prometteurs et déclins — matière pour le mercato."),
            ("msg_blessure", "Blessures", "Durée d'indisponibilité des joueurs blessés."),
            ("msg_staff", "Planning et staff", "Séances du préparateur, du recruteur et du kiné."),
            ("msg_transfert", "Rappel des offres en attente", "Rappel des offres non répondues dans la messagerie."),
            ("msg_contrat", "Fin de contrat", "Alerte avant le départ gratuit d'un joueur — recommandé."),
        ):
            card = QFrame(); card.setObjectName("OptionRow")
            col = QVBoxLayout(card); col.setContentsMargins(12, 7, 12, 7); col.setSpacing(1)
            box = QCheckBox(label); box.setMinimumHeight(22)
            default = (key != "msg_anniversaire")
            box.setChecked(bool(options.get(key, default)))
            self.msg_boxes[key] = box
            hint = QLabel(tip); hint.setObjectName("OptionHint"); hint.setWordWrap(True)
            hint.setMinimumWidth(0); hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            col.addWidget(box); col.addWidget(hint)
            ml.addWidget(card)

        media_card = QFrame(); media_card.setObjectName("OptionRow")
        mcol = QVBoxLayout(media_card); mcol.setContentsMargins(12, 7, 12, 7); mcol.setSpacing(1)
        self.media_gate_box = QCheckBox("Presse et rumeurs")
        self.media_gate_box.setChecked(bool(options.get("msg_media", False)))
        self.media_gate_box.setToolTip("La presse publie une synthèse des résultats des autres clubs et des rumeurs de transfert. Décoché : aucune nouvelle presse.")
        mhint = QLabel("Synthèse des résultats des autres clubs et rumeurs de transfert (désactivé par défaut).")
        mhint.setObjectName("OptionHint"); mhint.setWordWrap(True)
        mhint.setMinimumWidth(0); mhint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        mcol.addWidget(self.media_gate_box); mcol.addWidget(mhint)
        ml.addWidget(media_card)

        section(ml, "FAMILLES DE MESSAGES")
        family_card = QFrame(); family_card.setObjectName("OptionRow")
        fcol = QVBoxLayout(family_card); fcol.setContentsMargins(12, 8, 12, 8); fcol.setSpacing(5)
        family_hint = QLabel("Choisis les familles visibles dans le centre de courrier. Décocher masque les messages déjà reçus et les nouveaux.")
        family_hint.setObjectName("OptionHint"); family_hint.setWordWrap(True)
        family_hint.setMinimumWidth(0); family_hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        fcol.addWidget(family_hint)
        family_grid = QGridLayout(); family_grid.setHorizontalSpacing(14); family_grid.setVerticalSpacing(3)
        self.msg_category_boxes = {}
        family_defs = (
            ("msg_cat_dossiers", "Dossiers transferts / contrats", "Offres, ventes, arrivées, prêts et fins de contrat."),
            ("msg_cat_scouting", "Rapports de scouting", "Rapports express et approfondis sur les joueurs observés."),
            ("msg_cat_matchs", "Rapports de match", "Comptes-rendus et notes après les rencontres."),
            ("msg_cat_club", "Vie du club et alertes", "Nouvelles du club, blessures, chantiers terminés."),
            ("msg_cat_saison", "Bilans et transitions de saison", "Résumé de saison, nouvelle saison et événements majeurs."),
            ("msg_cat_carriere", "Offres de club (SECRET)", "Propositions confidentielles de changement de club."),
            ("msg_cat_systeme", "Informations système", "Messages techniques et rappels discrets."),
        )
        for index, (key, label, tip) in enumerate(family_defs):
            box = QCheckBox(label)
            box.setChecked(bool(options.get(key, True)))
            box.setToolTip(tip)
            self.msg_category_boxes[key] = box
            family_grid.addWidget(box, index // 2, index % 2)
        fcol.addLayout(family_grid)
        ml.addWidget(family_card)

        section(ml, "LECTURE")
        read_card = QFrame(); read_card.setObjectName("OptionRow")
        rcol = QVBoxLayout(read_card); rcol.setContentsMargins(12, 7, 12, 7); rcol.setSpacing(1)
        self.mark_read_box = QCheckBox("Marquer comme lu à l'ouverture")
        self.mark_read_box.setChecked(bool(options.get("msg_mark_read", True)))
        rhint = QLabel("Décoché : un message reste non lu tant que tu ne le marques pas manuellement.")
        rhint.setObjectName("OptionHint"); rhint.setWordWrap(True)
        rhint.setMinimumWidth(0); rhint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        rcol.addWidget(self.mark_read_box); rcol.addWidget(rhint)
        ml.addWidget(read_card)
        ml.addStretch(1)
        tabs.addTab(messaging, "MESSAGERIE")

        # ---------------- TRICHE ----------------
        if cheat_cb:
            cheat, cl = scroll_page()
            section(cl, "COUPS DE POUCE IMMÉDIATS")
            info = QLabel("Ces actions s'appliquent immédiatement à la carrière ouverte : aucune limite, aucune sanction du board.")
            info.setObjectName("OptionHint"); info.setWordWrap(True)
            cl.addWidget(info)
            grid = QGridLayout(); grid.setHorizontalSpacing(7); grid.setVerticalSpacing(7)
            cheat_actions = (("+ 50 000 €", "budget_50000"), ("+ 250 000 €", "budget_250000"),
                             ("+ 1 000 000 €", "budget_1000000"), ("CONDITION 100 %", "heal_condition"),
                             ("MORAL MAXIMUM", "morale_max"))
            for index, (label, code) in enumerate(cheat_actions):
                btn = QPushButton(label); btn.setMinimumHeight(40)
                btn.setStyleSheet("QPushButton{background:#241d0f;color:#e2c07a;border:1px solid #6f5a2e;"
                                  "border-radius:8px;font-weight:900;}"
                                  "QPushButton:hover{background:#33280f;border-color:#a8873f;}")
                btn.clicked.connect(lambda _=False, c=code: cheat_cb(c))
                grid.addWidget(btn, index // 3, index % 3)
            cl.addLayout(grid)
            cl.addStretch(1)
            tabs.addTab(cheat, "TRICHE")

        # ---------------- AIDE INTERACTIVE ----------------
        help_panel = HelpPanel()
        tabs.addTab(help_panel, "AIDE")

        # ---------------- PIED ----------------
        footer = QHBoxLayout(); footer.setSpacing(8)
        note = QLabel("Les réglages sont enregistrés dans options.json.")
        note.setObjectName("Muted"); note.setStyleSheet("font-size:7.5pt;")
        footer.addWidget(note); footer.addStretch()
        if bug_cb:
            bug = QPushButton("SIGNALER UN BUG")
            bug.setObjectName("settings_mini")
            bug.setToolTip("Créer un ZIP avec les logs et, si tu veux, la sauvegarde active.")
            bug.clicked.connect(lambda: bug_cb(self))
            footer.addWidget(bug)
        cancel = QPushButton("ANNULER"); cancel.setMinimumHeight(40); cancel.setMinimumWidth(120)
        cancel.clicked.connect(self.reject)
        save = QPushButton("ENREGISTRER"); save.setObjectName("Primary")
        save.setMinimumHeight(40); save.setMinimumWidth(190)
        save.clicked.connect(self.accept)
        footer.addWidget(cancel); footer.addWidget(save)
        root.addLayout(footer)

    def values(self):
        values = {"theme": self.theme.currentText(), "font_size": self.font_size.value(),
                  "window_mode": self.window_mode.currentText(),
                  "difficulty": self.difficulty.currentText(),
                  "brief_cadence": self.brief_cadence.currentText()}
        for key, box in getattr(self, "msg_boxes", {}).items():
            values[key] = bool(box.isChecked())
        for key, box in getattr(self, "msg_category_boxes", {}).items():
            values[key] = bool(box.isChecked())
        if hasattr(self, "mark_read_box"):
            values["msg_mark_read"] = bool(self.mark_read_box.isChecked())
        if hasattr(self, "media_gate_box"):
            values["msg_media"] = bool(self.media_gate_box.isChecked())
        return values


class TacticalList(QListWidget):
    def __init__(self, limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit = limit
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dropEvent(self, event):
        if self.limit is not None and event.source() is not self and self.count() >= self.limit:
            event.ignore()
            return
        super().dropEvent(event)


class BenchItemDelegate(QStyledItemDelegate):
    """Banc tactique : carte compacte avec avatar, nom, ligne d'infos et
    pastille de note coloree. Les donnees viennent de l'item (UserRole+2)."""

    HEIGHT=76

    def sizeHint(self,option,index):
        return QSize(240,self.HEIGHT)

    def paint(self,painter,option,index):
        data=index.data(Qt.UserRole+2)
        if not isinstance(data,dict) or not data.get("name"):
            return super().paint(painter,option,index)
        painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        rect=QRectF(option.rect).adjusted(3,2,-3,-2)
        selected=bool(option.state & QStyle.State_Selected)
        hover=bool(option.state & QStyle.State_MouseOver)
        unavailable=bool(index.data(Qt.UserRole+1))
        if selected:
            border=QColor("#8b78dc"); bg=QColor("#222e4f")
        elif hover:
            border=QColor("#3b4d72"); bg=QColor("#192337")
        else:
            border=QColor("#232e46"); bg=QColor("#141c2c")
        painter.setPen(QPen(border,1.4)); painter.setBrush(bg)
        painter.drawRoundedRect(rect,9,9)
        if selected:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#8b78dc"))
            painter.drawRoundedRect(QRectF(rect.left()+1,rect.top()+9,3,rect.height()-18),1.5,1.5)
        # avatar
        icon=index.data(Qt.DecorationRole)
        av=QRectF(rect.left()+9,rect.center().y()-19,38,38)
        try:
            if icon is not None: icon.paint(painter,av.toRect())
        except Exception:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor("#0f1725")); painter.drawRoundedRect(av,8,8)
        number=str(data.get("number") or "")
        if number:
            f=QFont("Segoe UI",6,QFont.Bold); painter.setFont(f)
            badge=QRectF(av.left()-1,av.bottom()-12,30,12)
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(8,13,22,230)); painter.drawRoundedRect(badge,4,4)
            painter.setPen(QColor("#ffe6a6")); painter.drawText(badge,Qt.AlignCenter,number)
        # pastille de note a droite
        note=data.get("note")
        badge_w=42.0
        if note is not None:
            try: note=float(note)
            except Exception: note=None
        if note is not None:
            col=QColor("#62e5a9") if note>=15 else QColor("#ffd166") if note>=12 else QColor("#c9d4e6")
            pill=QRectF(rect.right()-10-badge_w,rect.top()+7,badge_w,20)
            painter.setPen(QPen(col,1.1)); painter.setBrush(QColor(col.red(),col.green(),col.blue(),32))
            painter.drawRoundedRect(pill,6,6)
            f=QFont("Segoe UI",8,QFont.Bold); painter.setFont(f); painter.setPen(col)
            painter.drawText(pill,Qt.AlignCenter,f"{note:.1f}")
            form_label=str(data.get("form_label") or "")
            if form_label:
                f=QFont("Segoe UI",6,QFont.Bold); painter.setFont(f); painter.setPen(QColor("#8fa3bd"))
                painter.drawText(QRectF(pill.left(),pill.bottom()+2,badge_w,11),Qt.AlignCenter,form_label)
        text_left=rect.left()+55
        text_right=rect.right()-10-(badge_w+8 if note is not None else 0)
        text_w=max(24,int(text_right-text_left))
        # nom
        f=QFont("Segoe UI",9)
        f.setBold(not unavailable)
        painter.setFont(f); painter.setPen(QColor("#6f7d97") if unavailable else QColor("#eef3fb"))
        fm=QFontMetrics(f)
        painter.drawText(QRectF(text_left,rect.top()+7,text_w,14),Qt.AlignLeft|Qt.AlignVCenter,
                         fm.elidedText(str(data.get("name") or ""),Qt.ElideRight,text_w))
        # ligne d'infos
        f=QFont("Segoe UI",7); painter.setFont(f); fm=QFontMetrics(f)
        painter.setPen(QColor("#74839a") if unavailable else QColor("#93a6c0"))
        painter.drawText(QRectF(text_left,rect.top()+23,text_w,12),Qt.AlignLeft|Qt.AlignVCenter,
                         fm.elidedText(str(data.get("sub") or ""),Qt.ElideRight,text_w))
        # statistiques cles
        stats=str(data.get("stats") or "")
        if stats:
            f=QFont("Segoe UI",6,QFont.Bold); painter.setFont(f); fm=QFontMetrics(f)
            painter.setPen(QColor("#7f93ad") if unavailable else QColor("#8de5b9"))
            painter.drawText(QRectF(text_left,rect.top()+38,text_w,11),Qt.AlignLeft|Qt.AlignVCenter,
                             fm.elidedText(stats,Qt.ElideRight,text_w))
        # drapeaux (fin de contrat, liste...)
        flags=str(data.get("flags") or "")
        if flags:
            f=QFont("Segoe UI",6,QFont.Bold); painter.setFont(f)
            painter.setPen(QColor("#ffb36b") if "FIN" in flags else QColor("#c9a8ff"))
            painter.drawText(QRectF(text_left,rect.top()+52,text_w,11),Qt.AlignLeft|Qt.AlignVCenter,
                             QFontMetrics(f).elidedText(flags,Qt.ElideRight,text_w))
        painter.restore()


class PitchZone(QLabel):

    player_dropped = Signal(object,int,str)

    player_clicked = Signal(int)

    def __init__(self, zone_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zone_name=zone_name; self.position_label=zone_name; self.rating_role=zone_name
        self.player_id=None; self.player_label=""; self.player_rating=None
        self.player_status=""; self.player_number=0; self.kit=None; self.player_form=None; self.player_stats=""
        self._drag_start_pos=None; self._drag_started=False
        self.setAcceptDrops(True); self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(92,44); self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.setCursor(Qt.ArrowCursor)

    def set_position_label(self,label,rating_role=None):
        self.position_label=label
        if rating_role is not None: self.rating_role=rating_role
        self.update()

    def reset_zone(self):
        self.player_id=None; self.player_label=""; self.player_rating=None
        self.player_status=""; self.player_number=0; self.player_form=None; self.player_stats=""
        self.setCursor(Qt.ArrowCursor); self.update()

    def _edge(self):
        if self.player_status=="🟥": return QColor("#c9964a")
        if self.player_status: return QColor("#c96f7c")
        if self.player_rating is not None: return QColor("#5fae8a") if self.player_rating>=15 else QColor("#9b8cc9")
        return QColor("#3d5674")

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r=QRectF(self.rect()).adjusted(1,1,-1,-1)
        edge=self._edge()
        hover=self.underMouse()
        if self.player_id is None:
            p.setPen(QPen(QColor("#4a5f7d") if hover else QColor("#41546f"),1.3,Qt.DashLine))
            p.setBrush(QColor(10,16,29,205))
            p.drawRoundedRect(r,10,10)
            p.setPen(QColor("#8ba0ba")); f=QFont("Segoe UI",6,QFont.Bold); f.setPixelSize(8); p.setFont(f)
            fm=QFontMetrics(f)
            pos=fm.elidedText(self.position_label.upper(),Qt.ElideRight,int(r.width()-14))
            p.drawText(QRectF(r.left()+7,r.top()+4,r.width()-14,12),Qt.AlignLeft|Qt.AlignVCenter,pos)
            p.setPen(QColor("#b6c4d8")); f.setPixelSize(9); p.setFont(f)
            p.drawText(r.adjusted(4,13,-4,-4),Qt.AlignCenter,"+ DÉPOSER")
            p.end(); return
        bg=QLinearGradient(r.topLeft(),r.bottomLeft())
        bg.setColorAt(0.0,QColor("#1a2a44") if hover else QColor("#16243a"))
        bg.setColorAt(1.0,QColor("#0e1828"))
        p.setPen(QPen(edge.lighter(115) if hover else edge,1.6)); p.setBrush(bg)
        p.drawRoundedRect(r,9,9)
        # liseré de note a gauche
        p.setPen(Qt.NoPen); p.setBrush(edge)
        p.drawRoundedRect(QRectF(r.left()+1,r.top()+9,3,max(8,r.height()-18)),1.5,1.5)
        h=int(r.height())
        scale=min(1.0,max(0.0,(h-44)/34.0))
        # maillot : plus grand qu'avant, la tuile etant plus basse
        ks=int(min(40,max(20,min(h-10,r.width()*0.22))))
        kit_rect=QRectF(r.left()+7,r.center().y()-ks/2.0,ks,ks)
        if self.kit is not None and not self.kit.isNull():
            p.drawPixmap(kit_rect,self.kit,QRectF(self.kit.rect()))
        text_x=kit_rect.right()+8.0
        text_w=max(24.0,r.right()-9.0-text_x)
        # polices agrandies : le texte occupe la tuile raccourcie
        f_pos=QFont("Segoe UI",6,QFont.Bold); f_pos.setPixelSize(8+int(round(scale)))
        f_name=QFont("Segoe UI",9,QFont.Bold); f_name.setPixelSize(10+int(round(2*scale)))
        f_note=QFont("Segoe UI",9,QFont.Bold); f_note.setPixelSize(10+int(round(2*scale)))
        fm_pos=QFontMetrics(f_pos); fm_name=QFontMetrics(f_name); fm_note=QFontMetrics(f_note)
        gap=max(1,int(round(2*scale)))
        l1,l2,l3=fm_pos.height(),fm_name.height(),fm_note.height()
        block=l1+l2+l3+2*gap
        y0=r.top()+max(3.0,(h-block)/2.0)
        y1=y0; y2=y1+l1+gap; y3=y2+l2+gap
        num_txt=f"#{int(self.player_number):02d}" if self.player_number else ""
        num_w=fm_pos.horizontalAdvance(num_txt) if num_txt else 0
        if num_txt:
            p.setFont(f_pos); p.setPen(QColor("#ffe6a6"))
            p.drawText(QRectF(r.right()-9-num_w,y1,num_w,l1),Qt.AlignRight|Qt.AlignVCenter,num_txt)
        if self.player_status:
            p.setFont(f_pos); p.setPen(QColor("#e4b46a"))
            p.drawText(QRectF(r.right()-9-num_w-(18 if num_txt else 0),y1,14,l1),Qt.AlignCenter,self.player_status)
        # ligne 1 : poste
        p.setFont(f_pos); p.setPen(QColor("#93a7c0"))
        room=max(10,int(text_w-num_w-(18 if self.player_status else 0)))
        p.drawText(QRectF(text_x,y1,room,l1),Qt.AlignLeft|Qt.AlignVCenter,
                   fm_pos.elidedText(self.position_label.upper(),Qt.ElideRight,room))
        # ligne 2 : nom (raccourci "P. Nom" si la place manque)
        display_name=self.player_label
        if fm_name.horizontalAdvance(display_name)>text_w and " " in display_name:
            parts=display_name.split()
            short_name=f"{parts[0][:1]}. {' '.join(parts[1:])}"
            if fm_name.horizontalAdvance(short_name)<=text_w: display_name=short_name
        p.setFont(f_name); p.setPen(QColor("#f2f7fd"))
        p.drawText(QRectF(text_x,y2,text_w,l2),Qt.AlignLeft|Qt.AlignVCenter,
                   fm_name.elidedText(display_name,Qt.ElideRight,int(text_w)))
        # ligne 3 : note + forme
        note=f"{self.player_rating:.1f}" if self.player_rating is not None else "—"
        p.setFont(f_note); p.setPen(edge.lighter(135))
        note_w=fm_note.horizontalAdvance(note)
        p.drawText(QRectF(text_x,y3,note_w+2,l3),Qt.AlignLeft|Qt.AlignVCenter,note)
        if self.player_form is not None:
            rest=f"  ·  F{self.player_form}"
            room2=int(text_w-note_w-4)
            if room2>14:
                p.setPen(QColor("#9db0c6"))
                p.drawText(QRectF(text_x+note_w+4,y3,room2,l3),Qt.AlignLeft|Qt.AlignVCenter,
                           fm_note.elidedText(rest,Qt.ElideRight,room2))
        p.end()

    def dragEnterEvent(self,event):
        if event.mimeData().hasText(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self,event):
        payload=event.mimeData().text().split("||",1)
        if len(payload)!=2:
            event.ignore(); return
        try: pid=int(payload[0])
        except ValueError:
            event.ignore(); return
        self.player_id=pid; self.player_label=payload[1].split("•")[0].strip(); self.setCursor(Qt.OpenHandCursor)
        self.update()
        self.player_dropped.emit(self,pid,payload[1]); event.acceptProposedAction()

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and self.player_id is not None:
            self._drag_start_pos=event.pos(); self._drag_started=False; event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._drag_start_pos is not None and self.player_id is not None and event.buttons() & Qt.LeftButton:
            if (event.pos()-self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                mime=QMimeData(); mime.setText(f"{self.player_id}||{self.player_label} • {self.position_label}")
                drag=QDrag(self); drag.setMimeData(mime); self._drag_started=True; self._drag_start_pos=None; drag.exec(Qt.MoveAction); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton and self.player_id is not None and self._drag_start_pos is not None and not self._drag_started:
            self.player_clicked.emit(self.player_id)
        self._drag_start_pos=None
        super().mouseReleaseEvent(event)


class DraggableBench(QListWidget):

    player_returned = Signal(int)



    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        self.setDragEnabled(True); self.setAcceptDrops(True); self.setDragDropMode(QAbstractItemView.DragDrop)

        self.setDefaultDropAction(Qt.MoveAction); self.setSelectionMode(QAbstractItemView.SingleSelection)



    def startDrag(self,supportedActions):

        item=self.currentItem()

        if not item: return

        if bool(item.data(Qt.UserRole+1)):

            # Blesse/suspendu : visible mais NON integrable — jamais de drag depuis le banc.

            return

        mime=QMimeData(); mime.setText(f"{item.data(Qt.UserRole)}||{item.text()}")

        drag=QDrag(self); drag.setMimeData(mime); drag.exec(Qt.MoveAction)



    def dropEvent(self,event):

        if event.source() is self:

            super().dropEvent(event); return

        payload=event.mimeData().text().split("||",1)

        if len(payload)!=2:

            event.ignore(); return

        try: pid=int(payload[0])

        except ValueError:

            event.ignore(); return

        if not any(self.item(i).data(Qt.UserRole)==pid for i in range(self.count())):

            item=QListWidgetItem(payload[1].strip()); item.setData(Qt.UserRole,pid); self.addItem(item)

        self.player_returned.emit(pid); event.acceptProposedAction()

class ElidedLabel(QLabel):
    """QLabel qui coupe proprement le texte trop long (ellipse) et garde
    l'integralite dans l'infobulle : plus de texte qui deborde."""

    def __init__(self,text="",parent=None):
        super().__init__(parent)
        self._full=str(text or "")
        self.setTextFormat(Qt.PlainText)
        self.setToolTip(self._full)
        self._apply()

    def set_full_text(self,text):
        self._full=str(text or "")
        self.setToolTip(self._full)
        self._apply()

    def setText(self,text):
        self._full=str(text or "")
        self.setToolTip(self._full)
        self._apply()

    def full_text(self):
        return self._full

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._apply()

    def _apply(self):
        width=max(20,int(self.width())-2)
        try:
            fm=self.fontMetrics()
            shown=fm.elidedText(self._full,Qt.ElideRight,width)
        except Exception:
            shown=self._full
        if super().text()!=shown:
            super().setText(shown)


class FutsalCourt(QFrame):
    """A futsal court painted in Qt with tactical player zones layered above it.

    Le trace conserve un ratio 2:1 : dans un widget large ou haut, le terrain
    est centre et jamais ecrase."""
    COURT_RATIO = 2.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("TacticalCourt")
        self.vertical=False
        self.setMinimumSize(460,280)
        self.setStyleSheet("QFrame#TacticalCourt{border:1px solid #425276;border-radius:18px;background:#103c39;}")

    def court_rect(self):
        rect=QRectF(self.rect()).adjusted(12,12,-12,-12)
        if rect.width()<=1 or rect.height()<=1:
            return rect
        if rect.width()/rect.height() > self.COURT_RATIO:
            width=rect.height()*self.COURT_RATIO
            rect=QRectF(rect.center().x()-width/2,rect.top(),width,rect.height())
        else:
            height=rect.width()/self.COURT_RATIO
            rect=QRectF(rect.left(),rect.center().y()-height/2,rect.width(),height)
        return rect

    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        field=QRectF(self.rect()).adjusted(8,8,-8,-8)
        turf=QLinearGradient(field.topLeft(),field.bottomRight()); turf.setColorAt(0,QColor("#17635b")); turf.setColorAt(.55,QColor("#105148")); turf.setColorAt(1,QColor("#0c443f"))
        painter.setPen(Qt.NoPen); painter.setBrush(turf); painter.drawRoundedRect(field,14,14)
        rect=self.court_rect()
        if self.vertical:
            self._paint_vertical_court(painter,rect)
            painter.end(); return
        band=rect.width()/10
        for index in range(0,10,2):
            painter.setBrush(QColor(255,255,255,12)); painter.drawRoundedRect(QRectF(rect.left()+index*band,rect.top()+2,band,rect.height()-4),2,2)
        line=QPen(QColor(225,245,238,150),2); painter.setPen(line); painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect,14,14)
        cx,cy=rect.center().x(),rect.center().y(); circle=rect.height()*.23
        # Long axis runs left-to-right: goals and penalty areas sit on the short ends.
        painter.drawLine(QPointF(cx,rect.top()),QPointF(cx,rect.bottom())); painter.drawEllipse(QPointF(cx,cy),circle,circle)
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(235,245,240,190)); painter.drawEllipse(QPointF(cx,cy),3,3)
        painter.setPen(line); painter.setBrush(Qt.NoBrush)
        box_w,box_h=rect.width()*.19,rect.height()*.48
        painter.drawRoundedRect(QRectF(rect.left(),cy-box_h/2,box_w,box_h),8,8)
        painter.drawRoundedRect(QRectF(rect.right()-box_w,cy-box_h/2,box_w,box_h),8,8)
        goal_h=rect.height()*.18
        painter.drawRoundedRect(QRectF(rect.left()-9,cy-goal_h/2,10,goal_h),3,3)
        painter.drawRoundedRect(QRectF(rect.right()-1,cy-goal_h/2,10,goal_h),3,3)
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(235,245,240,180))
        painter.drawEllipse(QPointF(rect.left()+box_w*.68,cy),3,3)
        painter.drawEllipse(QPointF(rect.right()-box_w*.68,cy),3,3)
        painter.end()

    def _paint_vertical_court(self,painter,rect):
        """Terrain portrait : buts en haut/bas, ligne médiane horizontale."""
        band=rect.height()/10
        for index in range(0,10,2):
            painter.setBrush(QColor(255,255,255,12))
            painter.drawRoundedRect(QRectF(rect.left()+2,rect.top()+index*band,
                                           rect.width()-4,band),2,2)
        line=QPen(QColor(225,245,238,150),2)
        painter.setPen(line); painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect,14,14)
        cx,cy=rect.center().x(),rect.center().y()
        painter.drawLine(QPointF(rect.left(),cy),QPointF(rect.right(),cy))
        circle=rect.width()*.23
        painter.drawEllipse(QPointF(cx,cy),circle,circle)
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(235,245,240,190))
        painter.drawEllipse(QPointF(cx,cy),3,3)
        painter.setPen(line); painter.setBrush(Qt.NoBrush)
        box_w,box_h=rect.width()*.48,rect.height()*.19
        painter.drawRoundedRect(QRectF(cx-box_w/2,rect.top(),box_w,box_h),8,8)
        painter.drawRoundedRect(QRectF(cx-box_w/2,rect.bottom()-box_h,box_w,box_h),8,8)
        goal_w=rect.width()*.18
        painter.drawRoundedRect(QRectF(cx-goal_w/2,rect.top()-9,goal_w,10),3,3)
        painter.drawRoundedRect(QRectF(cx-goal_w/2,rect.bottom()-1,goal_w,10),3,3)
        painter.setPen(Qt.NoPen); painter.setBrush(QColor(235,245,240,180))
        painter.drawEllipse(QPointF(cx,rect.top()+box_h*.68),3,3)
        painter.drawEllipse(QPointF(cx,rect.bottom()-box_h*.68),3,3)


class TacticalBoard(FutsalCourt):
    """Terrain tactique : les zones sont des enfants positionnes en
    coordonnees relatives au terrain 2:1. Aucun QGridLayout ne peut donc
    ecraser le terrain ni faire deborder les tuiles."""

    COL_X={0:0.115,1:0.305,2:0.500,3:0.695,4:0.885}
    ROW_Y={0:0.255,1:0.500,2:0.745}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.zones={}
        self.positions={}
        self.vertical=False
        self.setMinimumSize(480,280)
        policy=QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self,width):
        if self.vertical:
            return int(min(500,max(400,width*2.0+26)))
        return int(min(560,max(300,width/self.COURT_RATIO+26)))

    def set_vertical(self,value=True):
        self.vertical=bool(value)
        self.COURT_RATIO=0.5 if self.vertical else 2.0
        if self.vertical:
            self.setMinimumSize(260,400)
            self.setMaximumHeight(500)
        else:
            self.setMinimumSize(480,280)
            self.setMaximumHeight(560)
        policy=QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.updateGeometry(); self.relayout(); self.update()

    def add_zone(self,name,widget):
        widget.setParent(self)
        widget.show()
        self.zones[name]=widget
        self.relayout()

    def set_positions(self,positions):
        self.positions=dict(positions or {})
        self.relayout()

    def relayout(self):
        if not self.zones: return
        court=self.court_rect()
        if court.width()<=20 or court.height()<=20: return
        # La largeur suit l'ecart entre colonnes : jamais de tuiles qui se touchent.
        if self.vertical:
            zone_w=int(max(72,min(120,court.width()*0.29)))
            zone_h=int(max(50,min(66,court.height()*0.105)))
        else:
            col_gap=court.width()*0.19
            row_gap=court.height()*0.245
            zone_w=int(max(112,min(224,court.width()*0.205)))
            zone_w=max(96,min(zone_w,int(col_gap)-12))
            zone_h=int(max(44,min(78,court.height()*0.175)))
            zone_h=max(42,min(zone_h,int(row_gap)-12))
        for name,zone in self.zones.items():
            row,col=self.positions.get(name,(1,2))
            try:
                if self.vertical:
                    cx=court.left()+court.width()*(0.20+0.30*int(row))
                    cy=court.bottom()-court.height()*(0.13+0.185*int(col))
                else:
                    cx=court.left()+court.width()*self.COL_X.get(int(col),0.5)
                    cy=court.top()+court.height()*self.ROW_Y.get(int(row),0.5)
            except Exception:
                cx=court.center().x(); cy=court.center().y()
            zone.setFixedSize(zone_w,zone_h)
            zone.move(int(round(cx-zone_w/2)),int(round(cy-zone_h/2)))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.relayout()


MATCH_ACTION_LABELS = {
    "kickoff": "ENGAGEMENT", "build": "CONSTRUCTION", "pass": "PASSE",
    "turnover": "INTERCEPTION", "shot": "TIR", "goal": "BUT", "save": "ARRÊT",
    "foul": "FAUTE", "corner": "CORNER", "free_kick": "COUP FRANC",
    "substitution": "REMPLACEMENT", "timeout": "TEMPS MORT", "ten_metre": "COUP FRANC 10 M",
}
# Le simple temps de possession n'est pas un temps fort : il ne remplit pas le bandeau.
MATCH_BANNER_QUIET = ("build",)

# Durée du clignotement "but" (ticks de 400 ms) et du ralentissement associé.
GOAL_FLASH_TICKS = 10
GOAL_SLOW_MS = 4500


class MatchActionBanner(QFrame):
    """Bandeau du direct : résumé des derniers temps forts, coloré par équipe.

    Chaque pastille montre l'heure, l'action (PASSE, TIR, BUT, FAUTE, CORNER…), son
    équipe par la couleur et une ligne de détail (buteur, passeur → récepteur, gardien…).
    Sur but, le bandeau clignote aux couleurs de l'équipe qui marque.
    """
    SLOTS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MatchBanner")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.home_name = "DOMICILE"; self.away_name = "EXTÉRIEUR"
        self.home_color = "#72dfbd"; self.away_color = "#ffbd73"
        self.elapsed_seconds = 0; self.score = (0, 0)
        self.action_text = "COUP D'ENVOI"
        self._entries = []
        self._flash_on = False; self._flash_color = QColor("#ffffff"); self._flash_ticks = 0
        self._flash_timer = None
        root = QVBoxLayout(self); root.setContentsMargins(12, 9, 12, 9); root.setSpacing(7)
        head = QHBoxLayout(); head.setSpacing(10)
        self.action_label = QLabel(self.action_text)
        self.action_label.setStyleSheet("font-size:11pt;font-weight:900;letter-spacing:1px;color:#e9edf7;")
        self.action_label.setMinimumWidth(0)
        self.hint_label = QLabel("Les actions s'ajoutent au fil du match, en bas de page.")
        self.hint_label.setObjectName("Muted"); self.hint_label.setStyleSheet("font-size:8pt;")
        self.hint_label.setMinimumWidth(0)
        self.clock_label = QLabel("00:00  •  0 — 0")
        self.clock_label.setStyleSheet("font-weight:900;color:#cdb8ff;")
        head.addWidget(self.action_label); head.addStretch(1); head.addWidget(self.hint_label); head.addWidget(self.clock_label)
        root.addLayout(head)
        self.chips_row = QHBoxLayout(); self.chips_row.setSpacing(7)
        root.addLayout(self.chips_row)
        self._slots = []
        for _ in range(self.SLOTS):
            chip = QFrame(); chip.setObjectName("MatchBannerSlot")
            inner = QVBoxLayout(chip); inner.setContentsMargins(8, 5, 8, 5); inner.setSpacing(1)
            header = QLabel(); header.setMinimumWidth(0)
            label = QLabel(); label.setMinimumWidth(0)
            detail = QLabel(); detail.setMinimumWidth(0)
            inner.addWidget(header); inner.addWidget(label); inner.addWidget(detail)
            self.chips_row.addWidget(chip, 1)
            self._slots.append({"frame": chip, "header": header, "label": label, "detail": detail})
        self._refresh_chips()

    # ------------------------------------------------------------------ réglages
    def set_teams(self, home_name, away_name, home_players=None, away_players=None):
        self.home_name = home_name or "DOMICILE"; self.away_name = away_name or "EXTÉRIEUR"
        self._refresh_chips()

    def set_colors(self, home_color, away_color):
        self.home_color = home_color or "#72dfbd"; self.away_color = away_color or "#ffbd73"
        self._refresh_chips()

    def set_clock(self, elapsed_seconds, home_goals, away_goals):
        self.elapsed_seconds = max(0, int(elapsed_seconds)); self.score = (int(home_goals), int(away_goals))
        self.clock_label.setText(f"{self.clock_text()}  •  {self.score[0]} — {self.score[1]}")

    def clock_text(self):
        return f"{self.elapsed_seconds // 60:02d}:{self.elapsed_seconds % 60:02d}"

    def clear(self):
        self.stop_flash()
        self._entries = []; self.elapsed_seconds = 0; self.score = (0, 0)
        self.action_text = "COUP D'ENVOI"; self.action_label.setText(self.action_text)
        self.action_label.setStyleSheet("font-size:11pt;font-weight:900;letter-spacing:1px;color:#e9edf7;")
        self.clock_label.setText("00:00  •  0 — 0")
        self._refresh_chips()

    # ------------------------------------------------------------------ actions
    def animate_action(self, side="h", kind="build", detail=""):
        label = MATCH_ACTION_LABELS.get(kind, "ACTION")
        self._paint_header(side, label)
        if kind not in MATCH_BANNER_QUIET:
            self.push_action(side, label, detail=detail)

    def animate_pass(self, side, receiver_index=0, detail=""):
        self.animate_action(side, "pass", detail=detail)

    def stop_animation(self):
        self.stop_flash()
        self.action_text = "COUP DE SIFFLET FINAL"
        self.action_label.setText(self.action_text)
        self.action_label.setStyleSheet("font-size:11pt;font-weight:900;letter-spacing:1px;color:#c5cce0;")

    def push_action(self, side, label, stamp=None, detail=""):
        if not label:
            return
        color = self.home_color if side == "h" else self.away_color
        name = self.home_name if side == "h" else self.away_name
        self._entries.append({"side": side, "label": str(label), "color": color,
                              "stamp": stamp or self.clock_text(), "team": self._initials(name),
                              "detail": str(detail)})
        del self._entries[:-self.SLOTS]
        self._refresh_chips()

    def rename_last_action(self, label):
        if self._entries:
            self._entries[-1]["label"] = str(label); self._refresh_chips()

    def entries(self):
        return list(self._entries)

    # ------------------------------------------------------------------ effet but (clignotement)
    def goal_flash(self, color):
        """Clignote le bandeau aux couleurs de l'équipe qui marque pendant quelques secondes."""
        self.stop_flash()
        self._flash_color = QColor(color)
        if not self._flash_color.isValid():
            self._flash_color = QColor("#ffffff")
        self._flash_on = False; self._flash_ticks = 0
        if self._flash_timer is None:
            self._flash_timer = QTimer(self)
            self._flash_timer.timeout.connect(self._tick_goal_flash)
        self._tick_goal_flash()
        self._flash_timer.start(400)

    def stop_flash(self):
        if self._flash_timer is not None:
            self._flash_timer.stop()
        self._flash_on = False; self._flash_ticks = 0
        self._flash_color = QColor("#ffffff")

    def _tick_goal_flash(self):
        self._flash_ticks += 1
        self._flash_on = not self._flash_on
        self._refresh_chips()
        if self._flash_ticks >= GOAL_FLASH_TICKS:
            self._flash_timer.stop()
            self._flash_on = False
            self._refresh_chips()

    # ------------------------------------------------------------------ interne
    def _initials(self, name):
        parts = [part for part in str(name).split() if part]
        return ("".join(part[0] for part in parts[:2]) or "FC").upper()

    def _paint_header(self, side, label):
        color = self.home_color if side == "h" else self.away_color
        self.action_text = label
        self.action_label.setText(label)
        self.action_label.setStyleSheet(f"font-size:11pt;font-weight:900;letter-spacing:1px;color:{color};")

    def _refresh_chips(self):
        visible = self._entries[-self.SLOTS:]
        for index, slot in enumerate(self._slots):
            position = index - (self.SLOTS - len(visible))
            self._paint_slot(slot, visible[position] if position >= 0 else None)

    def _chip_style(self, color_name, base_alpha=34, border_alpha=120, extra_border=""):
        c = QColor(color_name)
        if not c.isValid():
            c = QColor("#72dfbd")
        rules = [
            f"QFrame#MatchBannerChip{{background:rgba({c.red()},{c.green()},{c.blue()},{base_alpha});",
            f"border:1px solid rgba({c.red()},{c.green()},{c.blue()},{border_alpha});",
            f"border-left:4px solid {c.name()};border-radius:8px;}}",
        ]
        if extra_border:
            rules.insert(1, f"border:3px solid {extra_border};")
        return "".join(rules)

    def _paint_slot(self, slot, entry):
        frame = slot["frame"]; header = slot["header"]; label = slot["label"]; detail = slot["detail"]
        flashing = self._flash_on and entry is not None
        if entry is None:
            frame.setObjectName("MatchBannerSlot"); frame.setToolTip("")
            frame.setStyleSheet("QFrame#MatchBannerSlot{background:#111a2b;border:1px dashed #253247;border-radius:8px;}")
            header.setText("")
            label.setText("·"); label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color:#4d5b70;font-weight:900;")
            detail.setText("")
            return
        color = QColor(entry["color"])
        if not color.isValid():
            color = QColor("#72dfbd")
        frame.setObjectName("MatchBannerChip")
        frame.setToolTip(f"{entry['team']} • {entry['label']}" + (f" — {entry['detail']}" if entry['detail'] else ""))
        accent = color.name()
        flash_border = ""
        if flashing:
            fc = self._flash_color.lighter(150)
            flash_border = fc.name()
        frame.setStyleSheet(self._chip_style(accent, extra_border=flash_border))
        header.setText(f"{entry['stamp']}  •  {entry['team']}")
        header.setStyleSheet("font-size:7pt;font-weight:700;color:#9fb0c8;")
        label.setText(entry["label"]); label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setStyleSheet(f"font-size:9pt;font-weight:900;color:{color.lighter(135).name()};")
        if entry.get("detail"):
            detail.setText(entry["detail"]); detail.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            detail.setStyleSheet("font-size:7.5pt;color:#b9c6d6;")
        else:
            detail.setText("")
"""Widgets de présentation inspirés des écrans de gestion football.
Aucune logique métier : les données sont injectées par l'application.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class FMInfoPanel(QFrame):
    def __init__(self, title="PANNEAU", parent=None):
        super().__init__(parent)
        self.setObjectName("FMInfoPanel")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(7)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("FMPanelTitle")
        self.layout.addWidget(self.title_label)
        self.body = QVBoxLayout(); self.body.setSpacing(4)
        self.layout.addLayout(self.body)

    def set_lines(self, lines):
        while self.body.count():
            item = self.body.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for text, accent in lines:
            label = QLabel(str(text)); label.setWordWrap(True); label.setObjectName("FMPanelLine")
            if accent: label.setStyleSheet(f"color:{accent};font-weight:800;")
            self.body.addWidget(label)
        if not lines:
            label = QLabel("Aucune donnée disponible"); label.setObjectName("Muted"); self.body.addWidget(label)


class FMAttributeBar(QWidget):
    def __init__(self, label="ATTRIBUT", value=0, parent=None):
        super().__init__(parent)
        self.label = QLabel(label.upper()); self.label.setObjectName("FMAttrLabel")
        self.value_label = QLabel(); self.value_label.setObjectName("FMAttrValue")
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setTextVisible(False); self.bar.setFixedHeight(8)
        row = QHBoxLayout(self); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(7)
        row.addWidget(self.label); row.addWidget(self.bar, 1); row.addWidget(self.value_label)
        self.set_value(value)

    def set_value(self, value):
        value = max(0, min(100, int(value or 0))); self.bar.setValue(value); self.value_label.setText(str(value))
        color = "#52c98f" if value >= 70 else "#e4ad53" if value >= 45 else "#e66b78"
        self.bar.setStyleSheet(f"QProgressBar{{background:#172434;border:0;border-radius:4px;}} QProgressBar::chunk{{background:{color};border-radius:4px;}}")
        self.value_label.setStyleSheet(f"color:{color};font-weight:900;min-width:24px;")


class FMHeaderBar(QFrame):
    """Header compact : identité club, contexte de saison, date, budget et CTA."""
    continueClicked = None
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("FMHeaderBar")
        row = QHBoxLayout(self); row.setContentsMargins(12, 7, 12, 7); row.setSpacing(10)
        self.badge = QLabel("FC"); self.badge.setObjectName("FMHeaderBadge"); self.badge.setFixedSize(44, 44); self.badge.setAlignment(Qt.AlignCenter); row.addWidget(self.badge)
        identity = QVBoxLayout(); identity.setSpacing(0)
        self.club = QLabel("Votre club"); self.club.setObjectName("FMHeaderClub")
        self.context = QLabel("Ligue • Saison"); self.context.setObjectName("Muted")
        identity.addWidget(self.club); identity.addWidget(self.context); row.addLayout(identity)
        row.addStretch(1)
        info = QVBoxLayout(); info.setSpacing(0); self.date = QLabel("—"); self.date.setObjectName("FMHeaderDate"); self.budget = QLabel("Budget —"); self.budget.setObjectName("FMHeaderBudget"); info.addWidget(self.date); info.addWidget(self.budget); row.addLayout(info)
        self.continue_button = QLabel("CONTINUER")
        self.continue_button.setObjectName("FMContinueButton"); self.continue_button.setAlignment(Qt.AlignCenter); self.continue_button.setMinimumSize(132, 38); row.addWidget(self.continue_button)

    def set_data(self, club, context, date_text, budget):
        self.club.setText(str(club)); self.context.setText(str(context)); self.date.setText(str(date_text)); self.budget.setText(f"Budget  {int(budget):,} €".replace(",", " "))
