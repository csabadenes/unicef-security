import uuid

import mock
from django.contrib.admin.sites import AdminSite
from django.contrib.messages import get_messages
from django.contrib.messages.storage import default_storage
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse

import pytest
import requests

from unicef_security import admin
from unicef_security.graph import DJANGOUSERMAP as sync_field_map
from unicef_security.models import BusinessArea, Region, User


def test_admin_reverse():
    model = User
    page = "changelist"
    reversed = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{page}")
    assert reversed == admin.admin_reverse(User)


def test_region_admin_sync(monkeypatch, requests_mock):
    region_admin = admin.RegionAdmin(Region, AdminSite())

    with monkeypatch.context() as m:
        mock_load_region = mock.Mock()
        m.setattr('unicef_security.admin.load_region', mock_load_region)
        setattr(requests_mock, 'GET', {})

        with pytest.raises(AssertionError):
            mock_load_region.assert_called_with()

        region_admin.sync(requests_mock)
        mock_load_region.assert_called_with()


def test_business_area_admin_sync(monkeypatch, requests_mock):
    ba_admin = admin.BusinessAreaAdmin(BusinessArea, AdminSite())

    with monkeypatch.context() as m:
        mock_load_ba = mock.Mock()
        m.setattr('unicef_security.admin.load_business_area', mock_load_ba)
        setattr(requests_mock, 'GET', {})

        with pytest.raises(AssertionError):
            mock_load_ba.assert_called_with()

        ba_admin.sync(requests_mock)
        mock_load_ba.assert_called_with()


def test_business_area_admin_sync_err(monkeypatch, requests_mock):
    ba_admin = admin.BusinessAreaAdmin(BusinessArea, AdminSite())

    with monkeypatch.context() as m:
        mock_load_ba_err = mock.Mock(side_effect=Exception)
        m.setattr('unicef_security.admin.load_business_area', mock_load_ba_err)
        setattr(requests_mock, 'GET', {})

        with pytest.raises(AssertionError):
            mock_load_ba_err.assert_called_with()

        with pytest.raises(Exception):
            ba_admin.sync(requests_mock)
            # test logger msg

        mock_load_ba_err.assert_called_with()


class TestUserAdmin2():
    @classmethod
    def setup_class(cls):
        cls.TEST_AZURE_GRAPH_API_BASE_URL = 'https://test.com/123'
        cls.useradmin = admin.UserAdmin2(User, AdminSite)

    def test_is_linked(self):
        azure_mock = mock.Mock(return_value={"is_linked": True})
        assert self.useradmin.is_linked(azure_mock) is True

    @pytest.mark.django_db
    @pytest.mark.skip(reason="'impersonate' does not seem to exist")
    def test_impersonate(self, requests_mock):
        user = User()
        test_req = self.useradmin.impersonate(requests_mock, user.id)
        assert test_req.status_code == 200
        assert test_req.url == reverse('impersonate-start', args=[user.id])

    @pytest.mark.skip()
    @pytest.mark.django_db
    def test_sync_user(self, requests_mock, monkeypatch):
        user = User(display_name='test_dname', username='test_uname')
        user.save()

        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_page', mock.Mock())
        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_token', mock.Mock())
        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_record', mock.Mock())

        setattr(requests_mock, 'GET', {})
        setattr(requests_mock, 'META', {})
        setattr(requests_mock, 'COOKIES', {})
        setattr(requests_mock, 'session', {})
        setattr(requests_mock, '_messages', default_storage(requests_mock))

        # test sync without azure id
        self.useradmin.sync_user(requests_mock, user.id)
        assert "Cannot sync user without azure_id" == list(get_messages(requests_mock))[0].message

        # reset messages
        setattr(requests_mock, '_messages', [])
        # reset message backend storage with an empty message list..
        setattr(requests_mock, '_messages', default_storage(requests_mock))

        # test sync with azure id
        user.azure_id = uuid.uuid4()
        user.save()
        new_display_name = 'test_new_display_name'
        updated_usr_info = {'username': user.username}, \
            {'display_name': new_display_name, 'azure_id': user.azure_id}
        mock_azr_result = mock.Mock(return_value=updated_usr_info)
        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_record', mock_azr_result)
        self.useradmin.sync_user(requests_mock, user.id)
        user = User.objects.get(username=user.username)
        assert "User synchronized" == list(get_messages(requests_mock))[0].message
        assert user.display_name == new_display_name

    @pytest.mark.django_db
    def test_link_user_data(self, requests_mock, monkeypatch):
        user = User(username='test_uname', azure_id=uuid.uuid4())
        user.save()

        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_page', mock.Mock())
        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_token', mock.Mock())
        monkeypatch.setattr('unicef_security.graph.Synchronizer.get_record', mock.Mock())

        # a = {'username': user.username}, {'display_name': 'a', 'azure_id': user.azure_id}
        # monkeypatch.setattr('unicef_security.graph.Synchronizer.get_user', a)
        # get_user = mock.Mock(return_value={})
        # get_token = mock.Mock(return_value={})
        # search_users = mock.Mock(return_value=[])
        # a = mock.Mock(spec=['get_token'=get_token, 'get_user'=get_user, 'search_users'=search_users])
        # a = mock.Mock(spec=[get_token, get_user, search_users])
        # t_a = {'get_token':get_token, 'get_user':get_user, 'search_users':search_users}
        # a = mock.Mock()
        # a.configure_mock(**t_a)
        # monkeypatch.setattr('unicef_security.graph.Synchronizer', a)

        request_spec = {
            'GET': {},
            'META': {},
            'COOKIES': {},
            'session': {},
            'method': 'POST',
        }

        for k, v in request_spec.items():
            setattr(requests_mock, k, v)

        setattr(requests_mock, '_messages', default_storage(requests_mock))
        # setattr(requests_mock, 'GET', {})
        # setattr(requests_mock, 'META', {})
        # setattr(requests_mock, 'COOKIES', {})
        # setattr(requests_mock, 'session', {})
        # setattr(requests_mock, 'method', 'POST')
        # setattr(requests_mock, '_messages', default_storage(requests_mock))

        # test without user selection
        test_post = {'selection': None}
        setattr(requests_mock, 'POST', test_post)
        self.useradmin.link_user_data(requests_mock, user.id)

        print('1', get_messages(requests_mock))
        for msg in get_messages(requests_mock):
            print('1', msg)

        # test with user selection
        test_post['selection'] = {'id': user.id}
        setattr(requests_mock, 'POST', test_post)
        self.useradmin.link_user_data(requests_mock, user.id)

        print('2', get_messages(requests_mock))
        for msg in get_messages(requests_mock):
            print('2', msg)

    def test_link_user_data_err(self):
        pass

    def test_load(self):
        pass


class TestRoleform():
    pass
