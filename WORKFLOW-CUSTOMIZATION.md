# WORKFLOW CUSTOMIZATION - WAN 2.2

## Paramètres personnalisables

### 🎯 Actuellement supportés (handler v1)
- ✅ `prompt` : Prompt positif (node 227)
- ✅ `seed` : Seed pour reproductibilité (nodes 407/408)

### 🔧 À ajouter facilement

```python
def inject_params(workflow, params):
    """Injecte les paramètres personnalisés dans le workflow"""
    
    # 1. Prompts
    if params.get('prompt'):
        workflow['227']['inputs']['text'] = params['prompt']
    
    if params.get('negative_prompt'):
        workflow['228']['inputs']['text'] = params['negative_prompt']
    
    # 2. Résolution & durée
    if params.get('width'):
        workflow['335']['inputs']['width'] = params['width']
    
    if params.get('height'):
        workflow['335']['inputs']['height'] = params['height']
    
    if params.get('length'):  # Nombre de frames
        workflow['335']['inputs']['length'] = params['length']
    
    # 3. Frame rate
    if params.get('fps'):
        workflow['80']['inputs']['frame_rate'] = params['fps']
    
    # 4. RIFE interpolation
    if params.get('interpolation_multiplier'):
        workflow['369']['inputs']['multiplier'] = params['interpolation_multiplier']
    
    if params.get('rife_quality'):  # 'fast' ou 'quality'
        workflow['369']['inputs']['fast_mode'] = (params['rife_quality'] == 'fast')
    
    # 5. Sampling
    if params.get('steps'):
        workflow['407']['inputs']['steps'] = params['steps']
        workflow['408']['inputs']['steps'] = params['steps']
    
    if params.get('cfg'):
        workflow['407']['inputs']['cfg'] = params['cfg']
        workflow['408']['inputs']['cfg'] = params['cfg']
    
    # 6. Seeds
    if params.get('seed'):
        workflow['407']['inputs']['seed'] = params['seed']
        workflow['408']['inputs']['seed'] = params['seed'] + 1
    
    # 7. LoRA selection (strength reste à 1.0 - requis pour WAN)
    if params.get('lora_high_noise'):  # LoRA pour high noise model
        workflow['298']['inputs']['lora_name'] = params['lora_high_noise']
        # strength_model reste à 1.0 (pas touché)
    
    if params.get('lora_low_noise'):   # LoRA pour low noise model
        workflow['303']['inputs']['lora_name'] = params['lora_low_noise']
        # strength_model reste à 1.0 (pas touché)
    
    # 8. Video quality
    if params.get('crf'):  # 15=haute qualité, 23=normale, 28=basse
        workflow['80']['inputs']['crf'] = params['crf']
    
    return workflow
```

### 📊 Exemples de configurations

#### Configuration rapide (test)
```json
{
  "prompt": "cat playing with yarn",
  "width": 480,
  "height": 480,
  "length": 41,
  "fps": 16,
  "interpolation_multiplier": 2,
  "rife_quality": "fast",
  "steps": 8,
  "crf": 23
}
```
⏱️ Temps: ~2-3 min | 📦 Taille: ~500KB

#### Configuration standard (production)
```json
{
  "prompt": "beautiful sunset over mountains",
  "width": 720,
  "height": 720,
  "length": 81,
  "fps": 32,
  "interpolation_multiplier": 2,
  "rife_quality": "fast",
  "steps": 10,
  "crf": 19
}
```
⏱️ Temps: ~6-7 min | 📦 Taille: ~2MB

#### Configuration haute qualité
```json
{
  "prompt": "cinematic scene of a dragon flying",
  "width": 1024,
  "height": 576,
  "length": 121,
  "fps": 32,
  "interpolation_multiplier": 4,
  "rife_quality": "quality",
  "steps": 15,
  "crf": 15
}
```
⏱️ Temps: ~15-20 min | 📦 Taille: ~8-10MB

### 🎬 Résolutions supportées par WAN 2.2

| Résolution | Width x Height | Usage |
|------------|----------------|-------|
| 480p | 720 x 480 | Test rapide |
| SD | 720 x 576 | Standard |
| HD | 1280 x 720 | Haute définition |
| Square | 720 x 720 | Social media |
| Vertical | 576 x 1024 | Stories/TikTok |
| Cinematic | 1024 x 576 | 16:9 cinéma |

### ⚡ Impact sur les coûts

| Résolution | Length | Steps | Multiplier | Temps estimé | Coût A100 |
|------------|--------|-------|------------|--------------|-----------|
| 480x480 | 41 | 8 | 2x | 2-3 min | $0.10 |
| 720x720 | 81 | 10 | 2x | 6-7 min | $0.30 |
| 1024x576 | 121 | 15 | 4x | 15-20 min | $0.80 |

### 🚨 Limites techniques

- **VRAM max**: 80GB (A100)
- **Résolution max**: 1024x1024 (mais très lent)
- **Length max**: ~200 frames (avant OOM)
- **Steps optimal**: 8-15 (au-delà = peu d'amélioration)
- **CFG optimal**: 1-2 pour WAN (au-delà = artefacts)
- **LoRA strength**: DOIT rester à 1.0 (requirement WAN 2.2)

### 🔄 Workflow alternatifs possibles

1. **Sans RIFE** (plus rapide)
   - Supprimer node 369
   - Connecter node 269 directement à node 80
   - Temps: -50%

2. **Avec LoRA custom**
   - Remplacer `lora_name` dans nodes 298/303
   - Nécessite le LoRA sur le volume RunPod (`/runpod-volume/ComfyUI/models/loras/`)
   - ⚠️ Ne jamais modifier `strength_model` (doit rester à 1.0)

3. **Multi-résolution**
   - Générer en 480p
   - Upscale avec Ultimate SD Upscale
   - Meilleure qualité finale

### 🎯 Prochaine étape recommandée

Mettre à jour `handler_production.py` pour accepter ces paramètres :

```python
def handler(job):
    input_data = job['input']
    
    # Params par défaut
    params = {
        'prompt': input_data.get('prompt', 'A beautiful scene'),
        'width': input_data.get('width', 720),
        'height': input_data.get('height', 720),
        'length': input_data.get('length', 81),
        'fps': input_data.get('fps', 32),
        'steps': input_data.get('steps', 10),
        'seed': input_data.get('seed', random.randint(0, 999999)),
        # ... etc
    }
    
    workflow = load_workflow(input_data['workflow'])
    workflow = inject_params(workflow, params)
    # ... reste du handler
```

**Veux-tu que j'implémente ces améliorations dans le handler ?** 🚀
