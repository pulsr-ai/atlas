#!/usr/bin/env python3
"""
Final Integration Test with Proper File Handling
"""
import requests
import json
import time
import io

def run_final_integration_test():
    print("🚀 FINAL INTEGRATION TEST: Census + Atlas")
    print("=" * 60)
    
    # Get fresh authentication token
    print("🔐 Getting fresh authentication token...")
    try:
        # Request OTP
        login_response = requests.post(
            "http://localhost:8001/api/v1/auth/login",
            json={"email": "admin@example.com"}
        )
        if login_response.status_code != 200:
            print(f"❌ Failed to request OTP: {login_response.text}")
            return False
        
        session_data = login_response.json()
        session_id = session_data["session_id"]
        
        # Prompt for OTP
        otp_code = input("Enter OTP from Census console: ").strip()
        
        # Verify OTP
        verify_response = requests.post(
            "http://localhost:8001/api/v1/auth/verify-otp",
            json={"session_id": session_id, "otp_code": otp_code}
        )
        if verify_response.status_code != 200:
            print(f"❌ OTP verification failed: {verify_response.text}")
            return False
            
        auth_data = verify_response.json()
        access_token = auth_data["access_token"]
        print(f"✅ Authentication successful!")
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create document content
    print(f"\n1️⃣  DOCUMENT PREPARATION")
    print("-" * 30)
    
    document_content = """# Kubernetes Container Orchestration Guide

## Introduction to Kubernetes

Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. Originally developed by Google, it has become the de facto standard for container orchestration in cloud-native environments.

## Core Kubernetes Concepts

### Pods
Pods are the smallest deployable units in Kubernetes, containing one or more containers that share storage and network resources. Each pod gets its own IP address and can communicate with other pods in the cluster.

### Services
Services provide stable network endpoints for pods, enabling load balancing and service discovery. Types include ClusterIP, NodePort, LoadBalancer, and ExternalName services.

### Deployments
Deployments manage ReplicaSets and provide declarative updates for pods and replica sets. They handle rolling updates, rollbacks, and scaling operations.

### ConfigMaps and Secrets
ConfigMaps store configuration data as key-value pairs, while Secrets store sensitive information like passwords and tokens in base64-encoded format.

## Advanced Orchestration Features

### Auto-scaling
Horizontal Pod Autoscaler (HPA) automatically scales pods based on CPU utilization, memory usage, or custom metrics. Vertical Pod Autoscaler (VPA) adjusts resource requests and limits.

### Service Mesh Integration
Service mesh solutions like Istio provide advanced traffic management, security, and observability features for microservices communication.

### Ingress Controllers
Ingress controllers manage external access to services, providing HTTP/HTTPS routing, SSL termination, and load balancing capabilities.

### Persistent Storage
Kubernetes supports various storage options including local storage, network-attached storage, and cloud provider storage solutions through the Container Storage Interface (CSI).

## Best Practices

### Resource Management
- Define resource requests and limits for containers
- Use namespaces to organize resources
- Implement network policies for security
- Regular cluster maintenance and updates

### Monitoring and Logging
- Deploy monitoring solutions like Prometheus and Grafana
- Centralized logging with ELK stack or similar
- Set up alerting for critical system events
- Regular health checks and readiness probes

### Security Considerations
- Role-Based Access Control (RBAC) implementation
- Pod Security Policies and Pod Security Standards
- Network segmentation and encryption
- Regular security scanning and updates

This guide provides essential knowledge for effectively orchestrating containers with Kubernetes."""

    print(f"✅ Document prepared: Kubernetes Guide ({len(document_content):,} chars)")
    
    # Test Atlas document ingestion with simplified approach
    print(f"\n2️⃣  ATLAS DOCUMENT INGESTION")
    print("-" * 30)
    
    try:
        print("📤 Uploading document using proper multipart format...")
        
        # Create file-like object
        file_obj = io.BytesIO(document_content.encode('utf-8'))
        file_obj.name = 'kubernetes_guide.md'  # Set filename attribute
        
        # Proper multipart form data
        files = {
            'file': ('kubernetes_guide.md', file_obj, 'text/markdown')
        }
        data = {
            'directory_path': '/technical_guides'
        }
        
        upload_response = requests.post(
            "http://localhost:8000/api/v1/ingest",
            headers={"Authorization": f"Bearer {access_token}"},
            files=files,
            data=data
        )
        
        if upload_response.status_code == 200:
            doc_info = upload_response.json()
            print(f"✅ Document uploaded successfully!")
            print(f"   ID: {doc_info['id']}")
            print(f"   Name: {doc_info['name']}")
            print(f"   Directory: {doc_info['directory_path']}")
            print(f"   Version: {doc_info['version']}")
        else:
            print(f"❌ Upload failed:")
            print(f"   Status: {upload_response.status_code}")
            print(f"   Error: {upload_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False
    
    # Wait for processing
    print("⏳ Waiting for document processing...")
    time.sleep(6)
    
    # Test agentic retrieval
    print(f"\n3️⃣  AGENTIC RETRIEVAL TESTING")
    print("-" * 30)
    
    queries = [
        "What are the core concepts in Kubernetes?",
        "How does auto-scaling work in Kubernetes?",
        "What are the security best practices for Kubernetes?",
        "How do Services work in Kubernetes?",
        "What monitoring solutions should I use with Kubernetes?"
    ]
    
    successful_queries = 0
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/retrieve",
                headers=headers,
                json={"query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                chunks = result.get('results', [])
                reasoning = result.get('reasoning_path', {})
                
                print(f"   ✅ Found {len(chunks)} relevant chunks")
                print(f"   📊 Reasoning: {reasoning.get('chunks_identified', 0)} chunks identified")
                
                if chunks:
                    top_chunk = chunks[0]
                    print(f"   🎯 Top result: {top_chunk['content'][:120]}...")
                    
                successful_queries += 1
            else:
                print(f"   ❌ Query failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Query error: {e}")
        
        time.sleep(1)
    
    # Verify system state
    print(f"\n4️⃣  SYSTEM VERIFICATION")
    print("-" * 30)
    
    try:
        # Check documents
        docs_response = requests.get("http://localhost:8000/api/v1/documents", headers=headers)
        if docs_response.status_code == 200:
            docs = docs_response.json()
            print(f"✅ Knowledge base contains {len(docs)} documents")
            k8s_docs = [d for d in docs if 'kubernetes' in d.get('name', '').lower()]
            if k8s_docs:
                print(f"   Including new Kubernetes guide: {k8s_docs[0]['name']}")
        
        # Check directories
        dirs_response = requests.get("http://localhost:8000/api/v1/directories", headers=headers)
        if dirs_response.status_code == 200:
            dirs = dirs_response.json()
            print(f"✅ Directory structure: {len(dirs)} directories")
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
    
    # Final results
    print(f"\n{'=' * 60}")
    print("🎉 FINAL INTEGRATION TEST COMPLETE!")
    print("=" * 60)
    print(f"📊 Query Success Rate: {successful_queries}/{len(queries)}")
    print()
    if successful_queries == len(queries):
        print("🏆 ALL SYSTEMS OPERATIONAL!")
        print("✅ Census Authentication")
        print("✅ Document Ingestion & Chunking") 
        print("✅ Agentic Retrieval")
        print("✅ Knowledge Base Management")
        print()
        print("🚀 ATLAS KNOWLEDGE BASE READY FOR PRODUCTION!")
        return True
    else:
        print("⚠️  Some queries failed - system partially operational")
        return False

if __name__ == "__main__":
    success = run_final_integration_test()
    if success:
        print("\n✨ Integration test completed successfully!")
    else:
        print("\n❌ Integration test had issues")