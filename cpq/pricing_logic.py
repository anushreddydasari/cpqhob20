# Pricing Logic for CPQ System - Updated with Volume Discounts and Tiered Pricing

# Helper: get cost per user based on Excel tiers (volume discounts)
def get_cost_per_user(users):
    """Calculate per-user cost based on volume tiers"""
    if users <= 25:
        return 20.0
    elif users <= 50:
        return 18.0
    elif users <= 100:
        return 16.0
    elif users <= 250:
        return 14.0
    elif users <= 500:
        return 12.5
    elif users <= 1000:
        return 12.0
    elif users <= 2000:
        return 11.0
    elif users <= 5000:
        return 9.0
    elif users <= 10000:
        return 7.5
    elif users <= 30000:
        return 7.0
    else:
        return 6.5  # fallback for 30,000+ users

# Helper: get cost per GB based on Excel tiers (volume discounts)
def get_cost_per_gb(gb):
    """Calculate per-GB cost based on data volume tiers"""
    if gb <= 500:
        return 0.5
    elif gb <= 2500:
        return 0.4
    elif gb <= 5000:
        return 0.35
    elif gb <= 10000:
        return 0.3
    elif gb <= 20000:
        return 0.25
    elif gb <= 50000:
        return 0.2
    elif gb <= 100000:
        return 0.18
    elif gb <= 200000:
        return 0.17
    elif gb <= 500000:
        return 0.32
    elif gb <= 1000000:
        return 0.28
    elif gb <= 2000000:
        return 0.25
    else:
        return 0.22  # fallback for 2M+ GB

# Helper: get managed migration cost (Excel: Hours × Rate)
def get_managed_migration_cost(tier_level):
    """Calculate migration cost based on tier level and hourly rate"""
    hourly_rate = 150.0
    tier_hours = [2, 4, 10, 15, 30, 50, 80, 100, 125, 150, 200]
    hours = tier_hours[tier_level - 1] if 1 <= tier_level <= len(tier_hours) else 50
    return hours * hourly_rate

# Plan multipliers for different service levels
plan_multipliers = {
    "basic": 1.0,      # Base pricing
    "standard": 1.2,   # 20% premium for standard features
    "advanced": 1.5    # 50% premium for advanced features
}

# Migration type to tier level mapping
migration_tier_mapping = {
    "content": 1,      # Tier 1: 2 hours = $300
    "email": 2,        # Tier 2: 4 hours = $600
    "messaging": 3     # Tier 3: 10 hours = $1,500
}

# Instance costs by instance type (unchanged)
instance_costs = {
    "small": 500,
    "standard": 1000,
    "large": 2000,
    "extra_large": 3500
}

def calculate_quote(users, instance_type, instances, duration, migration_type, data_size):
    """
    Calculate quote for all three plans using tiered pricing with volume discounts
    
    Args:
        users (int): Number of users
        instance_type (str): Type of instance (small, standard, large, extra_large)
        instances (int): Number of instances
        duration (int): Duration in months
        migration_type (str): Type of migration (content, email, messaging)
        data_size (int): Data size in GB
    
    Returns:
        dict: Quote results for all three plans
    """
    # Get base pricing using volume discounts
    per_user_cost = get_cost_per_user(users)
    per_gb_cost = get_cost_per_gb(data_size)
    
    # Calculate base costs (not plan-adjusted yet)
    base_user_cost = users * per_user_cost
    base_data_cost = data_size * per_gb_cost
    
    # Get migration tier and calculate migration cost
    migration_tier = migration_tier_mapping.get(migration_type, 1)
    base_migration_cost = get_managed_migration_cost(migration_tier)
    
    # Instance cost calculation with duration multiplier
    instance_cost_per_instance = instance_costs.get(instance_type, instance_costs["standard"])
    instance_cost = instance_cost_per_instance * instances * duration

    results = {}

    # Calculate costs for each plan with multipliers
    for plan_name in ["basic", "standard", "advanced"]:
        plan_multiplier = plan_multipliers.get(plan_name, 1.0)
        
        # Apply plan multiplier to user and data costs
        user_cost = base_user_cost * plan_multiplier
        data_cost = base_data_cost * plan_multiplier
        
        # Migration cost is the same for all plans (one-time service)
        migration_cost = base_migration_cost
        
        # Calculate total cost
        total_cost = user_cost + data_cost + migration_cost + instance_cost

        results[plan_name] = {
            "perUserCost": per_user_cost * plan_multiplier,
            "perGBCost": per_gb_cost * plan_multiplier,
            "totalUserCost": user_cost,
            "dataCost": data_cost,
            "migrationCost": migration_cost,
            "instanceCost": instance_cost,
            "totalCost": total_cost
        }

    return results

def get_pricing_info():
    """
    Get pricing information for display purposes
    
    Returns:
        dict: All pricing information including tier structures
    """
    return {
        "user_tiers": {
            "description": "Per-user pricing based on volume",
            "tiers": [
                {"max_users": 25, "cost_per_user": 20.0},
                {"max_users": 50, "cost_per_user": 18.0},
                {"max_users": 100, "cost_per_user": 16.0},
                {"max_users": 250, "cost_per_user": 14.0},
                {"max_users": 500, "cost_per_user": 12.5},
                {"max_users": 1000, "cost_per_user": 12.0},
                {"max_users": 2000, "cost_per_user": 11.0},
                {"max_users": 5000, "cost_per_user": 9.0},
                {"max_users": 10000, "cost_per_user": 7.5},
                {"max_users": 30000, "cost_per_user": 7.0},
                {"max_users": "unlimited", "cost_per_user": 6.5}
            ]
        },
        "data_tiers": {
            "description": "Per-GB pricing based on data volume",
            "tiers": [
                {"max_gb": 500, "cost_per_gb": 0.5},
                {"max_gb": 2500, "cost_per_gb": 0.4},
                {"max_gb": 5000, "cost_per_gb": 0.35},
                {"max_gb": 10000, "cost_per_gb": 0.3},
                {"max_gb": 20000, "cost_per_gb": 0.25},
                {"max_gb": 50000, "cost_per_gb": 0.2},
                {"max_gb": 100000, "cost_per_gb": 0.18},
                {"max_gb": 200000, "cost_per_gb": 0.17},
                {"max_gb": 500000, "cost_per_gb": 0.32},
                {"max_gb": 1000000, "cost_per_gb": 0.28},
                {"max_gb": 2000000, "cost_per_gb": 0.25},
                {"max_gb": "unlimited", "cost_per_gb": 0.22}
            ]
        },
        "migration_tiers": {
            "description": "Migration costs based on complexity and hourly rate ($150/hour)",
            "tiers": [
                {"type": "content", "tier": 1, "hours": 2, "cost": 300},
                {"type": "email", "tier": 2, "hours": 4, "cost": 600},
                {"type": "messaging", "tier": 3, "hours": 10, "cost": 1500}
            ]
        },
        "plan_multipliers": {
            "description": "Plan multipliers applied to base costs",
            "multipliers": {
                "basic": 1.0,
                "standard": 1.2,
                "advanced": 1.5
            }
        },
        "instance_costs": instance_costs
    }
