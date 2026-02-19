#!/usr/bin/env python3
"""
Network Storage Setup Script
À lancer dans le Pod classique pour préparer la structure
"""

import os
import json
from pathlib import Path

def create_directory_structure():
    """Créer la structure de dossiers recommandée"""
    
    print("📁 Creating directory structure on network storage...")
    
    directories = [
        "/workspace/models/checkpoints",
        "/workspace/models/loras/action-lora",
        "/workspace/models/loras/character-loras", 
        "/workspace/models/embeddings",
        "/workspace/models/upscale_models",
        "/workspace/workflows",
        "/workspace/temp",
        "/workspace/cache/huggingface"
    ]
    
    created = []
    for dir_path in directories:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            created.append(dir_path)
            print(f"   ✅ {dir_path}")
        except Exception as e:
            print(f"   ❌ Failed to create {dir_path}: {e}")
    
    print(f"\n✅ Created {len(created)} directories")
    return created

def create_demo_workflows():
    """Créer des workflows de base pour la démo"""
    
    print("\n📋 Creating demo workflows...")
    
    # Workflow WAN T2V basique
    wan_t2v_workflow = {
        "3": {
            "inputs": {
                "seed": 42,
                "steps": 20, 
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "wan_2.2.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": 512,
                "height": 512, 
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": "Beautiful woman dancing, NSFW, high quality, 4K",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "blurry, low quality, distorted, bad anatomy",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "wan_demo",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }
    
    # Workflow avec LoRA
    wan_lora_workflow = {
        "3": {
            "inputs": {
                "seed": 42,
                "steps": 25,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras", 
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "wan_2.2.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "10": {
            "inputs": {
                "lora_name": "action-lora/fem_mast_v1.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["4", 0],
                "clip": ["4", 1]
            },
            "class_type": "LoraLoader"
        },
        "5": {
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": "fem_mast, dynamic movement, NSFW, high quality",
                "clip": ["10", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "blurry, low quality, static, boring",
                "clip": ["10", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "wan_lora_demo",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }
    
    workflows = {
        "wan-t2v-basic.json": wan_t2v_workflow,
        "wan-t2v-lora.json": wan_lora_workflow
    }
    
    created = []
    for filename, workflow in workflows.items():
        try:
            filepath = f"/workspace/workflows/{filename}"
            with open(filepath, 'w') as f:
                json.dump(workflow, f, indent=2)
            created.append(filename)
            print(f"   ✅ {filename}")
        except Exception as e:
            print(f"   ❌ Failed to create {filename}: {e}")
    
    print(f"\n✅ Created {len(created)} workflow files")
    return created

def check_models():
    """Vérifier quels modèles sont présents"""
    
    print("\n🔍 Checking for models...")
    
    model_paths = {
        "WAN 2.2": "/workspace/models/checkpoints/wan_2.2.safetensors",
        "Z-Image Turbo": "/workspace/models/checkpoints/z-image-turbo.safetensors",
        "Action LoRA": "/workspace/models/loras/action-lora/fem_mast_v1.safetensors"
    }
    
    found = {}
    for name, path in model_paths.items():
        exists = os.path.exists(path)
        found[name] = exists
        status = "✅ Found" if exists else "❌ Missing"
        size = ""
        
        if exists:
            try:
                size_bytes = os.path.getsize(path)
                size_mb = size_bytes / (1024 * 1024)
                size = f" ({size_mb:.1f} MB)"
            except:
                pass
        
        print(f"   {status} {name}{size}")
        if not exists:
            print(f"      Expected at: {path}")
    
    missing_count = sum(1 for v in found.values() if not v)
    if missing_count > 0:
        print(f"\n⚠️  {missing_count} models missing. Upload them to the paths shown above.")
        print("   You can test the serverless endpoint once models are uploaded.")
    else:
        print(f"\n🎉 All models found! Ready for serverless deployment.")
    
    return found

def create_info_file():
    """Créer un fichier d'info pour debug"""
    
    info = {
        "setup_timestamp": "2026-02-19",
        "version": "v1",
        "structure_created": True,
        "workflows_created": True,
        "notes": [
            "This storage is configured for RunPod Serverless ComfyUI-WAN",
            "Upload your models to /workspace/models/checkpoints/",
            "Upload your LoRAs to /workspace/models/loras/",
            "Workflows are in /workspace/workflows/",
            "Temp files go to /workspace/temp/"
        ]
    }
    
    try:
        with open("/workspace/SETUP_INFO.json", 'w') as f:
            json.dump(info, f, indent=2)
        print("\n📝 Created setup info file: /workspace/SETUP_INFO.json")
    except Exception as e:
        print(f"\n❌ Failed to create info file: {e}")

def main():
    print("🚀 RunPod Network Storage Setup Script")
    print("======================================")
    print("This script prepares your network storage for serverless ComfyUI-WAN")
    print()
    
    # Check if we're on network storage
    if not os.path.exists("/workspace"):
        print("❌ /workspace not found!")
        print("   Make sure network storage is mounted to /workspace")
        print("   Run this script inside a Pod with the volume mounted")
        return
    
    if not os.access("/workspace", os.W_OK):
        print("❌ /workspace not writable!")
        print("   Check volume mount permissions")
        return
    
    print("✅ Network storage detected and writable")
    
    # Setup
    create_directory_structure()
    create_demo_workflows() 
    check_models()
    create_info_file()
    
    print("\n" + "="*50)
    print("🎯 SETUP COMPLETE!")
    print("="*50)
    print()
    print("Next steps:")
    print("1. ✅ Directory structure created")
    print("2. ✅ Demo workflows created")
    print("3. 📁 Upload your models to /workspace/models/")
    print("4. 🛑 Stop this Pod (keep network storage)")
    print("5. 🚀 Deploy serverless endpoint with same storage")
    print("6. 🧪 Run test_client.py to demo")
    print()
    print("Need help? Check README.md for detailed instructions.")

if __name__ == "__main__":
    main()