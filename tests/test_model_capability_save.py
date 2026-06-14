"""
模型能力保存功能测试

测试模型能力配置的保存、更新和批量操作功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.model_capability_service import ModelCapabilityService


def _build_mock_mongo(mock_doc, modified_count=1):
    """构建 MongoDB mock 链：client[db] -> db.system_configs -> collection"""
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = mock_doc
    mock_update_result = Mock()
    mock_update_result.modified_count = modified_count
    mock_update_result.matched_count = 1
    mock_collection.update_one.return_value = mock_update_result

    mock_db = MagicMock()
    mock_db.system_configs = mock_collection

    mock_client = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=mock_db)

    return mock_client, mock_collection


class TestModelCapabilitySave:
    """模型能力保存功能测试"""

    def setup_method(self):
        self.service = ModelCapabilityService()

    def test_save_model_capability_update_existing(self):
        """测试更新已有模型的能力配置"""
        mock_doc = {
            "_id": "test_id",
            "llm_configs": [{
                "model_name": "qwen-turbo",
                "capability_level": 1,
                "suitable_roles": ["quick_analysis"],
                "features": ["tool_calling"],
                "recommended_depths": ["快速"]
            }]
        }
        mock_client, mock_collection = _build_mock_mongo(mock_doc)

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            result = self.service.save_model_capability(
                model_name="qwen-turbo",
                capability_level=3,
                suitable_roles=["both"],
                features=["tool_calling", "reasoning"],
                recommended_depths=["基础", "标准", "深度"],
                performance_metrics={"speed": 4, "cost": 3, "quality": 4}
            )

        assert result is True
        call_args = mock_collection.update_one.call_args
        updated_configs = call_args[0][1]["$set"]["llm_configs"]
        assert updated_configs[0]["capability_level"] == 3
        assert updated_configs[0]["features"] == ["tool_calling", "reasoning"]

    def test_save_model_capability_new_model(self):
        """测试新增不存在的模型能力配置"""
        mock_doc = {"_id": "test_id", "llm_configs": []}
        mock_client, mock_collection = _build_mock_mongo(mock_doc)

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            result = self.service.save_model_capability(
                model_name="new-model",
                capability_level=4,
                suitable_roles=["deep_analysis"],
                features=["tool_calling", "reasoning", "long_context"],
                recommended_depths=["深度", "全面"]
            )

        assert result is True
        call_args = mock_collection.update_one.call_args
        updated_configs = call_args[0][1]["$set"]["llm_configs"]
        assert len(updated_configs) == 1
        assert updated_configs[0]["model_name"] == "new-model"
        assert updated_configs[0]["capability_level"] == 4

    def test_save_model_capability_no_active_config(self):
        """测试没有激活配置时保存失败"""
        mock_client, mock_collection = _build_mock_mongo(None)
        mock_collection.find_one.return_value = None

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            result = self.service.save_model_capability(
                model_name="qwen-turbo",
                capability_level=3,
                suitable_roles=["both"],
                features=["tool_calling"],
                recommended_depths=["基础", "标准"]
            )

        assert result is False

    def test_save_model_capabilities_batch_success(self):
        """测试批量保存模型能力配置成功"""
        mock_doc = {
            "_id": "test_id",
            "llm_configs": [{
                "model_name": "qwen-turbo",
                "capability_level": 1,
                "suitable_roles": ["quick_analysis"],
                "features": ["tool_calling"],
                "recommended_depths": ["快速"]
            }]
        }
        mock_client, mock_collection = _build_mock_mongo(mock_doc)

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            capabilities = [
                {
                    "model_name": "qwen-turbo",
                    "capability_level": 2,
                    "suitable_roles": ["both"],
                    "features": ["tool_calling", "long_context"],
                    "recommended_depths": ["快速", "基础", "标准"]
                },
                {
                    "model_name": "new-model",
                    "capability_level": 4,
                    "suitable_roles": ["deep_analysis"],
                    "features": ["tool_calling", "reasoning"],
                    "recommended_depths": ["深度", "全面"]
                }
            ]

            result = self.service.save_model_capabilities_batch(capabilities)

        assert result["updated"] == 1
        assert result["added"] == 1
        assert result["failed"] == 0

    def test_save_model_capabilities_batch_with_missing_model_name(self):
        """测试批量保存时部分条目缺少 model_name"""
        mock_doc = {"_id": "test_id", "llm_configs": []}
        mock_client, mock_collection = _build_mock_mongo(mock_doc)

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            capabilities = [
                {
                    "model_name": "qwen-turbo",
                    "capability_level": 2,
                    "suitable_roles": ["both"],
                    "features": ["tool_calling"],
                    "recommended_depths": ["快速", "基础"]
                },
                {
                    "capability_level": 4,
                    "suitable_roles": ["deep_analysis"],
                    "features": ["tool_calling", "reasoning"],
                    "recommended_depths": ["深度", "全面"]
                }
            ]

            result = self.service.save_model_capabilities_batch(capabilities)

        assert result["updated"] == 0
        assert result["added"] == 1
        assert result["failed"] == 1

    def test_save_model_capabilities_batch_no_active_config(self):
        """测试批量保存时没有激活配置"""
        mock_client, mock_collection = _build_mock_mongo(None)
        mock_collection.find_one.return_value = None

        with patch('pymongo.MongoClient', return_value=mock_client), \
             patch('app.core.config.settings') as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017"
            mock_settings.MONGO_DB = "test_db"

            capabilities = [
                {
                    "model_name": "qwen-turbo",
                    "capability_level": 2,
                    "suitable_roles": ["both"],
                    "features": ["tool_calling"],
                    "recommended_depths": ["快速", "基础"]
                }
            ]

            result = self.service.save_model_capabilities_batch(capabilities)

        assert result["updated"] == 0
        assert result["added"] == 0
        assert result["failed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
