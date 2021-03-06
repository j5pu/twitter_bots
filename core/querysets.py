# -*- coding: utf-8 -*-
from django.db.models import Q, Count, Max
from django.db.models.query import QuerySet
from project.querysets import MyQuerySet
from core.scrapper.utils import is_lte_than_days_ago
from twitter_bots import settings


class TwitterBotQuerySet(MyQuerySet):
    q__avatar_passed = Q(proxy_for_usage__proxies_group__avatar_required_to_send_tweets=False) | \
                        Q(twitter_avatar_completed=True)
    q__bio_passed = Q(proxy_for_usage__proxies_group__bio_required_to_send_tweets=False) | \
                 Q(twitter_bio_completed=True)

    q__profile_passed = q__avatar_passed & q__bio_passed

    q__account_passed = Q(twitter_registered_ok=True) & \
                        Q(twitter_confirmed_email_ok=True) &\
                        Q(is_suspended=False)

    q__completed = q__profile_passed & q__account_passed

    q__not_dead_and_not_being_created = Q(is_being_created=False) & Q(is_dead=False)
    q__usable_regardless_of_proxy = q__not_dead_and_not_being_created & q__completed
    q__unusable_regardless_of_proxy = ~q__not_dead_and_not_being_created | ~q__completed

    q__with_proxy_connecting_ok = Q(proxy_for_usage__is_unavailable_for_use=False) &\
                                  Q(proxy_for_usage__is_in_proxies_txts=True)

    q__with_proxy_ok = Q(proxy_for_usage__isnull=False) & q__with_proxy_connecting_ok


    def with_some_account_registered(self):
        return self.filter(Q(email_registered_ok=True) | Q(twitter_registered_ok=True))

    def without_any_account_registered(self):
        return self.filter(email_registered_ok=False, twitter_registered_ok=False)

    def usable_regardless_of_proxy(self):
        """
        Devuelve bots con capacidad de poder ser usados, independientemente de como esté su proxy
        """

        return self.filter(self.q__usable_regardless_of_proxy)

    def unusable_regardless_of_proxy(self):
        return self.filter(self.q__unusable_regardless_of_proxy)

    def registrable(self):
        """
            Saca robots que puedan continuar el registro.

            No vamos a continuar con aquellos que:
                - estén siendo creados por el create_bots
                - estén muertos
                - tengan suspendido el email
                - estén registrados en twitter pero no tengan correo
                - su grupo no tenga habilitado el crear bots para sus proxies
                - el proxy no sea apto para hacer el registro
        """
        return self.filter(
            is_being_created=False,
            is_dead=False,
            is_suspended_email=False
        )\
        .exclude(Q(email_registered_ok=False) & Q(twitter_registered_ok=True))\
        .filter(proxy_for_usage__proxies_group__is_bot_creation_enabled=True)\
        .with_proxy_for_usage_ok_for_doing_registrations()

    def completable(self):
        """Devuelve los bots que pueden ser completados.

        No vamos a completar aquellos que:
            - estén muertos
            - su grupo no tenga habilitado el usar bots para sus proxies
            - el proxy no sea apto para usarlo
            - no tengan suspendido el correo y no confirmado el email
        """
        return self.filter(
            is_dead=False,
            proxy_for_usage__proxies_group__is_bot_usage_enabled=True,
        )\
            .with_proxy_connecting_ok()\
            .exclude(Q(is_suspended_email=True) & Q(twitter_confirmed_email_ok=False))

    def with_proxy_for_usage_ok_for_doing_registrations(self):
        """Filtra por bots que tengan proxies ok para poder registrarse"""
        qs = self.with_proxy_connecting_ok()\
            .filter(
                proxy_for_usage__is_unavailable_for_registration=False,
            )

        # sacamos sólo los que tengan proxies con phone_required a false, a no ser que cambiemos la
        # variable en el settings
        if not settings.REUSE_PROXIES_REQUIRING_PHONE_VERIFICATION:
            qs = qs.filter(proxy_for_usage__is_phone_required=False)

        return qs

    def with_proxy_connecting_ok(self):
        """Filtra por los bots que tengan sus proxies funcionando correctamente"""
        return self.filter(self.q__with_proxy_connecting_ok)

    def with_proxy_not_connecting_ok(self):
        return self.filter(~self.q__with_proxy_connecting_ok)

    def with_proxy_ok(self):
        return self.filter(self.q__with_proxy_ok)

    def without_proxy_ok(self):
        return self.filter(~self.q__with_proxy_ok)

    def unregistered(self):
        return self.filter(twitter_registered_ok=False)

    def on_running_projects(self):
        return self.filter(proxy_for_usage__proxies_group__projects__is_running=True)

    def completed(self):
        """De los bots que toma devuelve sólo aquellos que estén completamente creados"""
        return self.filter(self.q__completed).distinct()

    def uncompleted(self):
        return self.filter(~self.q__completed).distinct()

    def registered_but_not_completed(self):
        return self\
            .filter(twitter_registered_ok=True)\
            .filter(
                Q(twitter_confirmed_email_ok=False) |
                Q(twitter_avatar_completed=False) |
                Q(twitter_bio_completed=False) |
                Q(is_suspended=True)
            ).distinct()

    def twitteable_regardless_of_proxy(self):
        """
        Entre los que se pueden usar (indep. si funciona su proxy o no), excluye los que sean extractores
        """
        return self.usable_regardless_of_proxy().filter(extractor=None)

    def _annotate_tweets_queued_to_send(self):
        """Anota en la queryset la cuenta de tweets encolados pendientes de enviar por el bot"""
        return self.extra(
            select={
                'tweets_queued_to_send': """
                  select count(id) from project_tweet
                  WHERE project_tweet.bot_used_id = core_twitterbot.id
                  AND project_tweet.sending=FALSE AND project_tweet.sent_ok=FALSE
                """
            }
        )

    def without_tweet_to_send_queue_full(self):
        """Saca bots que no tengan llena su cola de tweets pendientes de enviar llena"""

        # valid_pks = [
        #     bot.pk
        #     for bot in self._annotate_tweets_queued_to_send()
        #     if bot.tweets_queued_to_send < settings.MAX_QUEUED_TWEETS_TO_SEND_PER_BOT
        # ]

        with_enough_space_on_queue_pks = []

        for bot in self:
            tweets_queued_to_send = bot.tweets.filter(sending=False, sent_ok=False).count()
            if tweets_queued_to_send < settings.MAX_QUEUED_TWEETS_TO_SEND_PER_BOT:
                with_enough_space_on_queue_pks.append(bot.pk)

        return self.filter(pk__in=with_enough_space_on_queue_pks)

    def order_by__tweets_queued_to_send(self):
        raise NotImplementedError

    def total_from_proxies_group(self, proxies_group):
        # puede ser que un mismo bot esté registrado y usando el mismo proxy, así que quitamos twitterbots duplicados
        return (self.using_proxies_group(proxies_group) | self.registered_by_proxies_group(proxies_group)).distinct()

    def registered_by_proxies_group(self, proxies_group):
        return self.filter(twitter_registered_ok=False, proxy_for_registration__proxies_group=proxies_group)

    def using_proxies_group(self, proxies_group):
        """Saca robots usándose en el grupo de proxies dado"""
        return self.filter(proxy_for_usage__proxies_group=proxies_group)

    def using_in_project(self, project):
        """Saca robots usándose en el proyecto dado"""
        return self.filter(proxy_for_usage__proxies_group__projects=project)

    def using_in_running_projects(self):
        """Saca bots usándose en proyectos que estén en ejecución"""
        return self.filter(proxy_for_usage__proxies_group__projects__is_running=True)

    def pendant_to_finish_creation(self):
        """Devuelve bots a poder ser completados por el bot_creation_finisher. Estos son:
            - bots que falten por registrar y puedan ser registrados
            - bots que estén registrados y falten por completar
        """
        not_registered_pks = self.unregistered().registrable().get_pks_distinct()
        registered_but_not_completed_pks = self.registered_but_not_completed().completable().get_pks_distinct()
        pks = list(set(list(not_registered_pks) + list(registered_but_not_completed_pks)))

        return self.filter(pk__in=pks)

    q__without_any_suspended_bot = ~(
        Q(is_suspended=True) |
        Q(num_suspensions_lifted__gt=0)
    )

    def filter_suspended_bots(self):
        return self.filter(
            (
                Q(proxy_for_usage__proxies_group__reuse_proxies_with_suspended_bots=False) &
                self.q__without_any_suspended_bot
            ) |
            (
                Q(proxy_for_usage__proxies_group__reuse_proxies_with_suspended_bots=True)
            )
        )\
        .distinct()

    def mentioned_by_bot(self, bot):
        return self.filter(mentions__bot_used=bot)

    def unmentioned_by_bot(self, bot):
        return self.exclude(mentions__bot_used=bot)

    def annotate__mctweets_received_count(self):
        """
        Anotamos la cuenta de mctweets que recibió cada twitterbot
        http://timmyomahony.com/blog/filtering-annotations-django/
        """
        return self.extra(
            select = {
                'mctweets_received_count': """
                Select count(*) from project_tweet as tweet
                JOIN project_tweet_mentioned_bots as mctweet on mctweet.tweet_id=tweet.id
                where mctweet.twitterbot_id=core_twitterbot.id
                """
            }
        )

    def one_per_subnet(self):
        """Filtra los bots para que no salgan varios de una misma subnet"""

        from core.models import TwitterBot, Proxy

        # saca los distintos proxies para estos bots
        distinct_proxies = TwitterBot.objects.get_distinct_proxies(self)

        # saca las distintas subnets de los bots
        distinct_subnets = Proxy.objects.get_subnets_24(distinct_proxies)

        twitter_bots_pks = []
        for subnet in distinct_subnets:
            bot = self.filter(proxy_for_usage__proxy__istartswith=subnet).values('pk').first()
            twitter_bots_pks.append(bot['pk'])

        return self.filter(pk__in=twitter_bots_pks)


class ProxyQuerySet(MyQuerySet):
    q__without_any_suspended_bot = ~(
        Q(twitter_bots_using__is_suspended=True) |
        Q(twitter_bots_using__num_suspensions_lifted__gt=0)
    )

    def connection_ok(self):
        """Saca proxies a los que se puede conectar"""
        return self.filter(is_in_proxies_txts=True, is_unavailable_for_use=False,)

    def connection_fail(self):
        """Saca proxies a los que no se puede conectar"""
        return self.filter(Q(is_in_proxies_txts=False) | Q(is_unavailable_for_use=False))

    def available_to_assign_bots_for_use(self):
        """Devuelve proxies disponibles para poder asignar a bots para su uso"""

        # base de proxies aptos usar robots ya registrados
        proxies_base = self\
            .connection_ok()\
            .with_proxies_group_assigned()\
            .with_proxies_group_enabling_bot_usage()

        available_proxies_for_usage_ids = []

        # cogemos todos los proxies sin bots
        proxies_without_bots = proxies_base.without_bots()
        available_proxies_for_usage_ids.extend([result['id'] for result in proxies_without_bots.values('id')])

        # de los proxies con bots, cogemos los que cumplan todas estas características:
        #   - que no tengan ningún robot muerto
        #   - que tengan un número de bots para uso inferior al límite marcado por su grupo
        proxies_with_bots = proxies_base\
            .with_enough_space_for_usage()
        available_proxies_for_usage_ids.extend([result['id'] for result in proxies_with_bots.values('id')])

        return self.filter(id__in=available_proxies_for_usage_ids)

    def unavailable_to_assign_bots_for_use(self):
        return self.subtract(self.available_to_assign_bots_for_use())

    def available_to_assign_bots_for_registration(self):
        """
        Devuelve proxies disponibles para crear un bot
        """

        # Base de proxies aptos para el registro. Colocamos filtros en el siguiente orden:
        #   1.  De subnets /24 disponibles para hacer registros. Lo colocamos primero por si se
        #       cambiaron los proxies recientemente y habían de la misma subnet.
        #   2.  Que tengan conectividad ok
        #   3.  Que permitan el registro de cuentas hotmail/outlook (is_unavailable_for_registration=False)
        #   4.  Que tengan asignado un grupo de proxies
        #   5.  Que su grupo tenga permitida la creación de nuevos bots
        #
        proxies_base = self\
            .with_enough_time_ago_for_last_registration_under_subnets_24()\
            .connection_ok()\
            .filter(is_unavailable_for_registration=False,)\
            .with_proxies_group_assigned()\
            .with_proxies_group_enabling_bot_creation()

        if not settings.REUSE_PROXIES_REQUIRING_PHONE_VERIFICATION:
            proxies_base = proxies_base.filter(is_phone_required=False)

        available_proxies_for_reg_ids = []

        # cogemos todos los proxies sin bots
        proxies_without_bots = proxies_base.without_bots()
        available_proxies_for_reg_ids.extend([result['id'] for result in proxies_without_bots.values('id')])

        # de los proxies con bots cogemos los que cumplan todas estas características:
        #   - que no tengan ningún robot muerto o suspendido
        #   - que tengan asignado una cantidad de bots inferior al límite para el registro
        #   - que su ip tenga un robot registrado como mínimo hace x días (configurado en su grupo)
        proxies_with_bots = proxies_base\
            .filter_suspended_bots()\
            .with_enough_space_for_registration()\
            .with_enough_time_ago_for_last_registration()
        available_proxies_for_reg_ids.extend([result['id'] for result in proxies_with_bots.values('id')])

        return self.filter(id__in=available_proxies_for_reg_ids)

    def unavailable_to_assign_bots_for_registration(self):
        return self.subtract(self.available_to_assign_bots_for_registration())

    def with_some_registered_bot(self):
        return self.filter(twitter_bots_registered__isnull=False).distinct()

    def without_any_bot_registered(self):
        return self.filter(twitter_bots_registered__isnull=True).distinct()

    def with_some_bot_using(self):
        return self.filter(twitter_bots_using__isnull=False).distinct()

    def without_bots_using(self):
        return self.filter(twitter_bots_using__isnull=True).distinct()

    def with_bots(self):
        """Devuelve todos aquellos proxies que estén o hayan sido usados por al menos un robot"""
        return self.with_some_registered_bot() | self.with_some_bot_using()

    def without_bots(self):
        return self.without_any_bot_registered() & self.without_bots_using()

    def with_proxies_group_assigned(self):
        return self.filter(proxies_group__isnull=False)

    def with_proxies_group_enabling_bot_creation(self):
        return self.filter(proxies_group__is_bot_creation_enabled=True)

    def with_proxies_group_enabling_bot_usage(self):
        return self.filter(proxies_group__is_bot_usage_enabled=True)

    def without_proxies_group_assigned(self):
        return self.filter(proxies_group__isnull=True)

    def without_any_suspended_bot(self):
        return self.filter(self.q__without_any_suspended_bot).distinct()

    def without_any_dead_bot(self):
        return self.filter(
            Q(twitter_bots_using__isnull=True) |
            Q(twitter_bots_using__is_dead=False)
        ).distinct()

    def filter_suspended_bots(self):
        """
        Según el grupo de proxies tenga marcada la opción de reusar proxies o no
        devolverá todos los proxies o sólo los que no tengan bots suspendidos
        """
        return self.filter(
            (
                Q(proxies_group__reuse_proxies_with_suspended_bots=False) &
                self.q__without_any_suspended_bot
            ) |
            (
                Q(proxies_group__reuse_proxies_with_suspended_bots=True)
            )
        )\
        .distinct()

    def with_some_dead_bot(self):
        return self.filter(twitter_bots_using__is_dead=True).distinct()

    def _annotate__num_bots_registered(self):
        return self.annotate(num_bots_registered=Count('twitter_bots_registered'))

    def _annotate__num_bots_using(self):
        """Añade el número de bots activos que hay usando el proxy"""
        return self.annotate(num_bots_using=Count('twitter_bots_using'))

    def _annotate__latest_bot_registered_date(self):
        return self.annotate(latest_bot_registered_date=Max('twitter_bots_registered__date'))

    def with_enough_space_for_registration(self):
        """Saca los que tengan espacio para crear nuevos bots"""
        proxies_with_enough_space_pks = []
        for proxy in self.select_related('proxies_group', 'twitter_bots_registered'):
            if proxy.twitter_bots_registered.count() < proxy.proxies_group.max_tw_bots_per_proxy_for_registration:
                proxies_with_enough_space_pks.append(proxy.pk)

        return self.filter(pk__in=proxies_with_enough_space_pks)

    def with_enough_space_for_usage(self):
        """Saca los que tengan espacio para crear nuevos bots"""
        proxies_with_enough_space_pks = []
        for proxy in self.all():
            if proxy.get_active_bots_using().count() < proxy.proxies_group.max_tw_bots_per_proxy_for_usage:
                proxies_with_enough_space_pks.append(proxy.pk)

        return self.filter(pk__in=proxies_with_enough_space_pks)

    def with_enough_time_ago_for_last_registration(self):
        """Sacas los proxies donde el último registro se realizó hace el tiempo suficiente para crear nuevo bot"""
        proxies_with_enought_time_ago_pks = []
        for proxy in self._annotate__latest_bot_registered_date():
            if proxy.twitter_bots_registered.exists():
                latest_bot_is_old_enough = is_lte_than_days_ago(
                    proxy.latest_bot_registered_date,
                    proxy.proxies_group.min_days_between_registrations_per_proxy
                )
                if latest_bot_is_old_enough:
                    proxies_with_enought_time_ago_pks.append(proxy.pk)
            else:
                # si el proxy no tiene bots, obviamente es válido
                proxies_with_enought_time_ago_pks.append(proxy.pk)

        return self.filter(pk__in=proxies_with_enought_time_ago_pks)

    def with_subnet_24(self, subnet_24):
        return self.filter(proxy__startswith=subnet_24)

    def with_enough_time_ago_for_last_registration_under_subnets_24(self):
        """Saca los proxies de cada subnet /24 donde el último registro se realizó hace el tiempo
        suficiente para registrar bots en nuevos proxies bajo esa misma subnet.

        Por ejemplo, si tenemos 40 proxies bajo la subnet s1 y el último bot de ahí
        se registró hace 5 minutos, entonces no escogeremos ningún proxy de esa subnet
        """
        from core.models import Proxy, TwitterBot

        proxies_with_enought_time_ago_pks = []

        subnets = Proxy.objects.get_subnets_24(self)
        for subnet in subnets:
            proxies_in_subnet = self.with_subnet_24(subnet)
            bots_registered_in_subnet = TwitterBot.objects.filter(proxy_for_registration__in=proxies_in_subnet)
            if bots_registered_in_subnet:
                # si la subnet tiene algún proxy con bot registrado, comprobamos que la última
                # fecha de registro tenga la antiguedad mínima necesaria
                last_bot_registered = bots_registered_in_subnet.latest('date')
                last_bot_is_old_enough = is_lte_than_days_ago(
                    last_bot_registered.date,
                    last_bot_registered.get_group().min_days_between_registrations_per_proxy_under_same_subnet
                )
                if last_bot_is_old_enough:
                    proxies_with_enought_time_ago_pks.extend(proxies_in_subnet.values_list('pk', flat=True))
            else:
                # si la subnet no tiene ningún proxy que tenga un bot registrado, entonces agregamos todos sus proxies
                proxies_with_enought_time_ago_pks.extend(proxies_in_subnet.values_list('pk', flat=True))

        return self.filter(pk__in=proxies_with_enought_time_ago_pks)

    def using_in_running_projects(self):
        """Saca proxies usándose en proyectos que estén en ejecución"""
        return self.filter(proxies_group__projects__is_running=True)

    def for_group(self, group):
        return self.filter(proxies_group=group)

    def with_some_suspended_bot(self):
        return self.filter(
            Q(twitter_bots_using__is_suspended=True) |
            Q(twitter_bots_using__num_suspensions_lifted__gt=0)
        ).distinct()

    def valid_for_assign_proxies_group(self):
        """Saca proxies válidos para asignarles un grupo"""
        return self.without_bots().filter(is_in_proxies_txts=True)

    def with_completed_bots(self):
        """Saca proxies que tengan al menos un bot completamente creado"""
        return self.filter(
            twitter_bots_using__is_being_created=False,
            twitter_bots_using__is_dead=False,
            twitter_bots_using__is_suspended=False,
            twitter_bots_using__twitter_registered_ok=True,
            twitter_bots_using__twitter_confirmed_email_ok=True,
            twitter_bots_using__twitter_avatar_completed=True,
            twitter_bots_using__twitter_bio_completed=True,
        )

    def without_completed_bots(self):
        """Saca proxies que no tengan ningún bot completamente creado"""
        return self.filter(
            Q(twitter_bots_using__is_dead=True) |
            Q(twitter_bots_using__is_suspended=True) |
            Q(twitter_bots_using__twitter_registered_ok=False) |
            Q(twitter_bots_using__twitter_confirmed_email_ok=False) |
            Q(twitter_bots_using__twitter_avatar_completed=False) |
            Q(twitter_bots_using__twitter_bio_completed=False)
        )

    def invalid_for_assign_proxies_group(self):
        return self.subtract(self.valid_for_assign_proxies_group())
