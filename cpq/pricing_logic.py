# Pricing Logic for CPQ System

# UPDATED Pricing nested by migration type and plan (per user and per GB)
pricing = {
    "content": {
        "basic": {"user_cost": 30.0, "gb_cost": 1.0},
        "standard": {"user_cost": 35.0, "gb_cost": 1.50},
        "advanced": {"user_cost": 40.0, "gb_cost": 1.80},
    },
    "email": {
        "basic": {"user_cost": 15.0, "gb_cost": 0.0},
        "standard": {"user_cost": 15.0, "gb_cost": 0.0},
        "advanced": {"user_cost": 15.0, "gb_cost": 0.0},
    },
    "messaging": {
        "basic": {"user_cost": 18.0, "gb_cost": 0.0},
        "standard": {"user_cost": 22.0, "gb_cost": 0.0},
        "advanced": {"user_cost": 34.0, "gb_cost": 0.0},
    }
}

# Migration costs nested by migration type and plan
migration_costs = {
    "content": {
        "basic": 300,
        "standard": 300,
        "advanced": 300
    },
    "email": {
        "basic": 400,
        "standard": 600,
        "advanced": 800
    },
    "messaging": {
        "basic": 400,
        "standard": 600,
        "advanced": 800
    }
}

# Instance costs by instance type
instance_costs = {
    "small": 500,
    "standard": 1000,
    "large": 2000,
    "extra_large": 3500
}

def calculate_quote(users, instance_type, instances, duration, migration_type, data_size):
    """
    Calculate quote for all three plans (basic, standard, advanced)
    
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
    # Instance cost calculation with duration multiplier
    instance_cost_per_instance = instance_costs.get(instance_type, instance_costs["standard"])
    instance_cost = instance_cost_per_instance * instances * duration  # multiplied by duration

    results = {}

    # Iterate explicitly over plan names
    for plan_name in ["basic", "standard", "advanced"]:
        plan_price = pricing.get(migration_type, {}).get(plan_name, {"user_cost": 0, "gb_cost": 0})

        user_cost = plan_price["user_cost"] * users  # NOT multiplied by duration
        data_cost = plan_price["gb_cost"] * data_size  # NOT multiplied by duration

        migration_cost = migration_costs.get(migration_type, {}).get(plan_name, 300)

        total_cost = user_cost + data_cost + migration_cost + instance_cost

        results[plan_name] = {
            "perUserCost": plan_price["user_cost"],
            "perGBCost": plan_price["gb_cost"],
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
        dict: All pricing information
    """
    return {
        "pricing": pricing,
        "migration_costs": migration_costs,
        "instance_costs": instance_costs
    }
