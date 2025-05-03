"""Implementation of custom metadata creation functionality."""

import logging
from typing import List, Optional, Dict, Any
from pyatlan.model.typedef import AttributeDef, CustomMetadataDef
from pyatlan.model.enums import AtlanCustomAttributePrimitiveType

from client import get_atlan_client

# Configure logging
logger = logging.getLogger(__name__)


def create_custom_metadata(
    display_name: str,
    attributes: List[Dict[str, Any]],
    description: Optional[str] = None,
    emoji: Optional[str] = None,
    logo_url: Optional[str] = None,
    locked: bool = False,
) -> Dict[str, Any]:
    """Create a custom metadata definition in Atlan.

    Args:
        display_name (str): Display name for the custom metadata
        attributes (List[Dict[str, Any]]): List of attribute definitions. Each attribute should have:
            - display_name (str): Display name for the attribute
            - attribute_type (str): Type of the attribute (from AtlanCustomAttributePrimitiveType)
            - description (str, optional): Description of the attribute
            - multi_valued (bool, optional): Whether the attribute can have multiple values
            - options_name (str, optional): Name of options for enumerated types
        description (str, optional): Description of the custom metadata
        emoji (str, optional): Emoji to use as the logo
        logo_url (str, optional): URL to use for the logo
        locked (bool, optional): Whether the custom metadata definition should be locked

    Returns:
        Dict[str, Any]: Response from the creation request containing:
            - created: Boolean indicating if creation was successful
            - guid: GUID of the created custom metadata definition
            - error: Error message if creation failed

    Raises:
        Exception: If there's an error during creation
    """
    try:
        logger.info(f"Creating custom metadata definition: {display_name}")

        # Get Atlan client first to fail early if there are connection issues
        try:
            client = get_atlan_client()
        except Exception as e:
            error_msg = f"Failed to initialize Atlan client: {str(e)}"
            logger.error(error_msg)
            return {
                "created": False,
                "error": error_msg
            }

        # Create base custom metadata definition
        logger.debug("Creating base custom metadata definition")
        cm_def = CustomMetadataDef.create(display_name=display_name)

        # Set custom metadata description if provided
        if description:
            logger.debug(f"Setting custom metadata description: {description}")
            cm_def.description = description

        # Add attribute definitions
        attribute_defs = []
        for attr in attributes:
            try:
                # Parse and validate attribute type
                try:
                    attr_type = getattr(AtlanCustomAttributePrimitiveType, attr["attribute_type"].upper())
                except (AttributeError, KeyError) as e:
                    error_msg = f"Invalid attribute type for {attr.get('display_name', 'unknown')}: {attr.get('attribute_type')}"
                    logger.error(error_msg)
                    return {
                        "created": False,
                        "error": error_msg
                    }
                
                # Create attribute definition
                attr_def = AttributeDef.create(
                    display_name=attr["display_name"],
                    attribute_type=attr_type,
                    options_name=attr.get("options_name"),
                    multi_valued=attr.get("multi_valued", False)
                )

                # Set attribute description if provided
                if attr.get("description"):
                    logger.debug(f"Setting description for attribute {attr['display_name']}: {attr['description']}")
                    attr_def.description = attr["description"]

                attribute_defs.append(attr_def)
                logger.debug(f"Added attribute: {attr['display_name']} of type {attr_type}")
            except KeyError as e:
                error_msg = f"Missing required field in attribute definition: {str(e)}"
                logger.error(error_msg)
                return {
                    "created": False,
                    "error": error_msg
                }

        # Set attributes on custom metadata definition
        cm_def.attribute_defs = attribute_defs
        logger.debug(f"Added {len(attribute_defs)} attribute definitions")

        # Set logo options
        if emoji:
            logger.debug(f"Setting emoji logo: {emoji}")
            try:
                cm_def.options = CustomMetadataDef.Options.with_logo_as_emoji(
                    emoji=emoji,
                    locked=locked
                )
            except Exception as e:
                error_msg = f"Failed to set emoji logo: {str(e)}"
                logger.error(error_msg)
                return {
                    "created": False,
                    "error": error_msg
                }
        elif logo_url:
            logger.debug(f"Setting logo URL: {logo_url}")
            try:
                cm_def.options = CustomMetadataDef.Options.with_logo_from_url(
                    url=logo_url,
                    locked=locked
                )
            except Exception as e:
                error_msg = f"Failed to set logo URL: {str(e)}"
                logger.error(error_msg)
                return {
                    "created": False,
                    "error": error_msg
                }

        # Create the custom metadata definition
        logger.info("Sending creation request to Atlan")
        try:
            response = client.typedef.create(cm_def)
            if response and hasattr(response, 'custom_metadata_defs'):
                custom_metadata_defs = response.custom_metadata_defs
                if isinstance(custom_metadata_defs, list) and custom_metadata_defs:
                    first_def = custom_metadata_defs[0]
                    if hasattr(first_def, 'guid'):
                        logger.info(f"Custom metadata definition created with GUID: {first_def.guid}")
                        return {
                            "created": True,
                            "guid": first_def.guid
                        }
            
            # If we get here, the response didn't have the expected structure
            logger.error("Unexpected response structure")
            logger.debug(f"Response: {response}")
            return {
                "created": False,
                "error": "Custom metadata was created but unable to retrieve GUID"
            }
        except Exception as e:
            error_msg = f"Failed to create custom metadata: {str(e)}"
            logger.error(error_msg)
            logger.debug("Custom metadata definition that failed:", cm_def)
            return {
                "created": False,
                "error": error_msg
            }

    except Exception as e:
        error_msg = f"Unexpected error creating custom metadata: {str(e)}"
        logger.error(error_msg)
        logger.exception("Exception details:")
        return {
            "created": False,
            "error": error_msg
        }