"""Wizard deploy commands"""
import os
import sys
import time
from typing import Optional


class WizardCommands:
    """Deploy wizard for GPU instances"""

    def __init__(self, api_client):
        self.api = api_client

    def get_vast_api_key(self) -> Optional[str]:
        """Get Vast API key from config or environment"""
        # Try environment variable first
        api_key = os.environ.get('VAST_API_KEY')
        if api_key:
            return api_key

        # Try to get from API
        try:
            result = self.api.call("GET", "/api/v1/settings", silent=True)
            if result:
                return result.get('vast_api_key')
        except:
            pass

        return None

    def deploy(
        self,
        gpu_name: str = None,
        speed: str = "fast",
        max_price: float = 2.0,
        region: str = "global"
    ):
        """
        Deploy a GPU instance using the wizard strategy.

        Strategy:
        1. Search for offers matching criteria
        2. Create batch of 5 machines in parallel
        3. Wait up to 90s for any to become ready
        4. If none ready, try another batch (up to 3 batches)
        5. First machine with SSH ready wins, others are destroyed
        """
        print(f"\n🚀 Wizard Deploy Starting\n")
        print("=" * 60)
        print(f"   GPU:       {gpu_name or 'Any'}")
        print(f"   Speed:     {speed}")
        print(f"   Max Price: ${max_price}/hr")
        print(f"   Region:    {region}")
        print("=" * 60)

        # Import the wizard service
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        try:
            from src.services.deploy_wizard import (
                DeployWizardService,
                DeployConfig,
                BATCH_SIZE,
                MAX_BATCHES,
                BATCH_TIMEOUT
            )
        except ImportError as e:
            print(f"❌ Could not import wizard service: {e}")
            print("   Make sure you're running from the dumontcloud directory")
            sys.exit(1)

        # Get API key
        api_key = self.get_vast_api_key()
        if not api_key:
            print("❌ No Vast.ai API key found")
            print("   Set VAST_API_KEY environment variable or configure via settings")
            sys.exit(1)

        print(f"\n📡 Step 1: Searching for offers...")

        # Create wizard service
        wizard = DeployWizardService(api_key)

        # Create config
        config = DeployConfig(
            speed_tier=speed,
            gpu_name=gpu_name,
            region=region,
            max_price=max_price,
            disk_space=50,
            setup_codeserver=True,
        )

        # Get offers
        offers = wizard.get_offers(config)

        if not offers:
            print("❌ No offers found matching criteria")
            print("💡 Try relaxing filters (higher price, different GPU, different region)")
            sys.exit(1)

        print(f"   ✓ Found {len(offers)} offers")

        # Show top 5 offers
        print("\n   Top offers:")
        for i, offer in enumerate(offers[:5]):
            print(f"   {i+1}. {offer.get('gpu_name')} - ${offer.get('dph_total', 0):.3f}/hr - {offer.get('inet_down', 0):.0f} Mbps")

        # Start deploy
        print(f"\n🔄 Step 2: Starting multi-start deployment...")
        print(f"   Strategy: Create {BATCH_SIZE} machines per batch, up to {MAX_BATCHES} batches")
        print(f"   Timeout: {BATCH_TIMEOUT}s per batch")

        job = wizard.start_deploy(config)

        # Poll for completion
        start_time = time.time()
        last_status = None

        while True:
            job = wizard.get_job(job.id)

            if job.status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"\n   [{elapsed}s] Status: {job.status}")
                print(f"   {job.message}")

                if job.status == 'creating':
                    print(f"   Batch {job.batch}/{MAX_BATCHES} - Machines created: {len(job.machines_created)}")
                elif job.status == 'waiting':
                    print(f"   Machines created: {job.machines_created}")

                last_status = job.status

            if job.status in ['completed', 'failed']:
                break

            time.sleep(2)

        # Handle result
        print("\n" + "=" * 60)

        if job.status == 'failed':
            print(f"❌ Deploy failed: {job.error}")
            print(f"\n   Machines tried: {job.machines_tried}")
            print(f"   Machines created: {len(job.machines_created)}")
            print(f"   Machines destroyed: {len(job.machines_destroyed)}")
            sys.exit(1)

        result = job.result
        print(f"\n✅ Deploy Complete!\n")
        print(f"📋 Instance Details:")
        print("-" * 40)
        print(f"   Instance ID: {result['instance_id']}")
        print(f"   GPU:         {result.get('gpu_name', 'Unknown')}")
        print(f"   IP:          {result['public_ip']}")
        print(f"   SSH Port:    {result['ssh_port']}")
        print(f"   Price:       ${result.get('dph_total', 0):.3f}/hr")
        print(f"   Speed:       {result.get('inet_down', 0):.0f} Mbps")
        print(f"   Ready in:    {result.get('ready_time', 0):.1f}s")
        print("-" * 40)
        print(f"\n🔗 SSH Command:")
        print(f"   {result['ssh_command']}")

        if result.get('codeserver_port'):
            print(f"\n💻 Code Server:")
            print(f"   http://{result['public_ip']}:{result['codeserver_port']}")

        # Save instance ID for later use
        print(f"\n💾 Instance ID saved: {result['instance_id']}")

        return result
