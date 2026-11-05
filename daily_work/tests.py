from django.test import SimpleTestCase

from daily_work.categories import (
    allowed_update_fields,
    categories_for_function_names,
)


class CategoryMappingTests(SimpleTestCase):
    def test_every_role_sees_every_field(self):
        fields = allowed_update_fields(["PRODUCT DEVELOPMENT"])
        self.assertEqual(
            fields,
            allowed_update_fields(["MMR"]),
        )
        self.assertEqual(
            fields,
            [
                "production_update",
                "price_value",
                "packaging_user_experience",
                "performance_accuracy",
                "b2c",
                "b2b",
                "gov_semi",
                "cashflow",
                "new_customer",
                "repeat_order",
            ],
        )

    def test_function_label_does_not_hide_fields(self):
        self.assertEqual(
            categories_for_function_names(["NPD", "MMR", "P&S"]),
            ["PRODUCTION", "PRODUCT DEVELOPMENT", "MMR", "SALES"],
        )
        self.assertEqual(len(allowed_update_fields()), 10)
