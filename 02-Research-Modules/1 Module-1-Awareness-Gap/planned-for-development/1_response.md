if url.startswith("/"): # URLs starting with / are inherently schemeless.
url = to_str(\_encode_target(url))
destination_scheme = None
else:
parsed_url = parse_url(url)
destination_scheme = parsed_url.scheme
url = to_str(parsed_url.url)

        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if release_conn is None:
            release_conn = preload_content

        # Check host
        if assert_same_host and not self.is_same_host(url):
            raise HostChangedError(self, url, retries)

        conn = None

        # Track whether `conn` needs to be released before
        # returning/raising/recursing. Update this variable if necessary, and
        # leave `release_conn` constant throughout the function. That way, if
        # the function recurses, the original value of `release_conn` will be
        # passed down into the recursive call, and its value will be respected.
        #
        # See issue #651 [1] for details.
        #
        # [1] <https://github.com/urllib3/urllib3/issues/651>
        release_this_conn = release_conn

        http_tunnel_required = connection_requires_http_tunnel(
            self.proxy, self.proxy_config, destination_scheme
        )

        # Merge the proxy headers. Only done when not using HTTP CONNECT. We
        # have to copy the headers dict so we can safely change it without those
        # changes being reflected in anyone else's copy.
        if not http_tunnel_required:
            headers = headers.copy()  # type: ignore[attr-defined]
            headers.update(self.proxy_headers)  # type: ignore[union-attr]

        # Must keep the exception bound to a separate variable or else Python 3
        # complains about UnboundLocalError.
        err = None

        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False

        # Rewind body position, if needed. Record current position
        # for future rewinds in the event of a redirect/retry.
        body_pos = set_file_position(body, body_pos)

        try:
            # Request a connection from the queue.
            timeout_obj = self._get_timeout(timeout)
            conn = self._get_conn(timeout=pool_timeout)

            conn.timeout = timeout_obj.connect_timeout  # type: ignore[assignment]

            # Is this a closed/new connection that requires CONNECT tunnelling?
            if self.proxy is not None and http_tunnel_required and conn.is_closed:
                try:
                    self._prepare_proxy(conn)
                except (BaseSSLError, OSError, SocketTimeout) as e:
                    self._raise_timeout(
                        err=e, url=self.proxy.url, timeout_value=conn.timeout
                    )
                    raise

            # If we're going to release the connection in ``finally:``, then
            # the response doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = conn if not release_conn else None

            # Make the request on the HTTPConnection object

>           response = self._make_request(

                conn,
                method,
                url,
                timeout=timeout_obj,
                body=body,
                headers=headers,
                chunked=chunked,
                retries=retries,
                response_conn=response_conn,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:788:

---

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:493: in \_make_request
conn.request(
.venv/lib/python3.12/site-packages/urllib3/connection.py:500: in request
self.endheaders()
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1333: in endheaders
self.\_send_output(message_body, encode_chunked=encode_chunked)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1093: in \_send_output
self.send(msg)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1037: in send
self.connect()

---

self = <UnixHTTPConnection(host='localhost', port=80) at 0x10a8f87d0>

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

>       sock.connect(self.unix_socket)
>
> E FileNotFoundError: [Errno 2] No such file or directory

.venv/lib/python3.12/site-packages/docker/transport/unixconn.py:26: FileNotFoundError

During handling of the above exception, another exception occurred:

self = <docker.transport.unixconn.UnixHTTPAdapter object at 0x10a98fc50>, request = <PreparedRequest [GET]>, stream = False
timeout = Timeout(connect=60, read=60, total=None), verify = True, cert = None, proxies = OrderedDict()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:

>           resp = conn.urlopen(

                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

.venv/lib/python3.12/site-packages/requests/adapters.py:645:

---

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:842: in urlopen
retries = retries.increment(
.venv/lib/python3.12/site-packages/urllib3/util/retry.py:498: in increment
raise reraise(type(error), error, \_stacktrace)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/urllib3/util/util.py:38: in reraise
raise value.with_traceback(tb)
.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:788: in urlopen
response = self.\_make_request(
.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:493: in \_make_request
conn.request(
.venv/lib/python3.12/site-packages/urllib3/connection.py:500: in request
self.endheaders()
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1333: in endheaders
self.\_send_output(message_body, encode_chunked=encode_chunked)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1093: in \_send_output
self.send(msg)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1037: in send
self.connect()

---

self = <UnixHTTPConnection(host='localhost', port=80) at 0x10a8f87d0>

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

>       sock.connect(self.unix_socket)
>
> E urllib3.exceptions.ProtocolError: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/docker/transport/unixconn.py:26: ProtocolError

During handling of the above exception, another exception occurred:

self = <docker.api.client.APIClient object at 0x10a98fec0>

    def _retrieve_server_version(self):
        try:

>           return self.version(api_version=False)["ApiVersion"]

                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.venv/lib/python3.12/site-packages/docker/api/client.py:223:

---

.venv/lib/python3.12/site-packages/docker/api/daemon.py:181: in version
return self.\_result(self.\_get(url), json=True)
^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/utils/decorators.py:44: in inner
return f(self, \*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/api/client.py:246: in \_get
return self.get(url, **self.\_set_request_timeout(kwargs))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:605: in get
return self.request("GET", url, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:592: in request
resp = self.send(prep, **send_kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:706: in send
r = adapter.send(request, \*\*kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

---

self = <docker.transport.unixconn.UnixHTTPAdapter object at 0x10a98fc50>, request = <PreparedRequest [GET]>, stream = False
timeout = Timeout(connect=60, read=60, total=None), verify = True, cert = None, proxies = OrderedDict()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            resp = conn.urlopen(
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

        except (ProtocolError, OSError) as err:

>           raise ConnectionError(err, request=request)
>
> E requests.exceptions.ConnectionError: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/requests/adapters.py:660: ConnectionError

The above exception was the direct cause of the following exception:

    @pytest.fixture(scope="session")
    def postgres_url() -> AsyncIterator[str]:
        """Start a disposable Postgres and return an asyncpg URL."""

>       with PostgresContainer("postgres:16-alpine") as pg:

             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

app/tests/conftest.py:25:

---

.venv/lib/python3.12/site-packages/testcontainers/postgres/**init**.py:59: in **init**
super().**init**(image=image, **kwargs)
.venv/lib/python3.12/site-packages/testcontainers/core/container.py:86: in **init**
self.\_docker = DockerClient(**(docker_client_kw or {}))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/testcontainers/core/docker_client.py:73: in **init**
self.client = docker.from_env(**kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/client.py:94: in from_env
return cls(
.venv/lib/python3.12/site-packages/docker/client.py:45: in **init**
self.api = APIClient(\*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/api/client.py:207: in **init**
self.\_version = self.\_retrieve_server_version()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

---

self = <docker.api.client.APIClient object at 0x10a98fec0>

    def _retrieve_server_version(self):
        try:
            return self.version(api_version=False)["ApiVersion"]
        except KeyError as ke:
            raise DockerException(
                'Invalid response from docker daemon: key "ApiVersion"'
                ' is missing.'
            ) from ke
        except Exception as e:

>           raise DockerException(

                f'Error while fetching server API version: {e}'
            ) from e

E docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/docker/api/client.py:230: DockerException
****************\_\_**************** ERROR at setup of test_insert_pipeline_is_idempotent_on_duplicate ****************\_\_****************

self = <docker.transport.unixconn.UnixHTTPConnectionPool object at 0x10a98fc80>, method = 'GET', url = '/version', body = None
headers = {'User-Agent': 'docker-sdk-python/7.1.0', 'Accept-Encoding': 'gzip, deflate', 'Accept': '_/_', 'Connection': 'keep-alive'}
retries = Retry(total=0, connect=None, read=False, redirect=None, status=None), redirect = False, assert_same_host = False
timeout = Timeout(connect=60, read=60, total=None), pool_timeout = None, release_conn = False, chunked = False, body_pos = None
preload_content = False, decode_content = False, response_kw = {}, destination_scheme = None, conn = None, release_this_conn = True
http_tunnel_required = False, err = None, clean_exit = False

    def urlopen(  # type: ignore[override]
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        redirect: bool = True,
        assert_same_host: bool = True,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        pool_timeout: int | None = None,
        release_conn: bool | None = None,
        chunked: bool = False,
        body_pos: _TYPE_BODY_POSITION | None = None,
        preload_content: bool = True,
        decode_content: bool = True,
        **response_kw: typing.Any,
    ) -> BaseHTTPResponse:
        """
        Get a connection from the pool and perform an HTTP request. This is the
        lowest level call for making a request, so you'll need to specify all
        the raw details.

        .. note::

           More commonly, it's appropriate to use a convenience method
           such as :meth:`request`.

        .. note::

           `release_conn` will only behave as expected if
           `preload_content=False` because we want to make
           `preload_content=False` the default behaviour someday soon without
           breaking backwards compatibility.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Configure the number of retries to allow before raising a
            :class:`~urllib3.exceptions.MaxRetryError` exception.

            If ``None`` (default) will retry 3 times, see ``Retry.DEFAULT``. Pass a
            :class:`~urllib3.util.retry.Retry` object for fine-grained control
            over different types of retries.
            Pass an integer number to retry connection errors that many times,
            but no other types of errors. Pass zero to never retry.

            If ``False``, then retries are disabled and any exception is raised
            immediately. Also, instead of raising a MaxRetryError on redirects,
            the redirect response will be returned.

        :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

        :param redirect:
            If True, automatically handle redirects (status codes 301, 302,
            303, 307, 308). Each redirect counts as a retry. Disabling retries
            will disable redirect, too.

        :param assert_same_host:
            If ``True``, will make sure that the host of the pool requests is
            consistent else will raise HostChangedError. When ``False``, you can
            use the pool on an HTTP proxy and request foreign hosts.

        :param timeout:
            If specified, overrides the default timeout for this one
            request. It may be a float (in seconds) or an instance of
            :class:`urllib3.util.Timeout`.

        :param pool_timeout:
            If set and the pool is set to block=True, then this method will
            block for ``pool_timeout`` seconds and raise EmptyPoolError if no
            connection is available within the time period.

        :param bool preload_content:
            If True, the response's body will be preloaded into memory.

        :param bool decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param release_conn:
            If False, then the urlopen call will not release the connection
            back into the pool once a response is received (but will release if
            you read the entire contents of the response such as when
            `preload_content=True`). This is useful if you're not preloading
            the response's content immediately. You will need to call
            ``r.release_conn()`` on the response ``r`` to return the connection
            back into the pool. If None, it takes the value of ``preload_content``
            which defaults to ``True``.

        :param bool chunked:
            If True, urllib3 will send the body using chunked transfer
            encoding. Otherwise, urllib3 will send the body using the standard
            content-length form. Defaults to False.

        :param int body_pos:
            Position to seek to in file-like body in the event of a retry or
            redirect. Typically this won't need to be set because urllib3 will
            auto-populate the value when needed.
        """
        # Ensure that the URL we're connecting to is properly encoded
        if url.startswith("/"):
            # URLs starting with / are inherently schemeless.
            url = to_str(_encode_target(url))
            destination_scheme = None
        else:
            parsed_url = parse_url(url)
            destination_scheme = parsed_url.scheme
            url = to_str(parsed_url.url)

        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if release_conn is None:
            release_conn = preload_content

        # Check host
        if assert_same_host and not self.is_same_host(url):
            raise HostChangedError(self, url, retries)

        conn = None

        # Track whether `conn` needs to be released before
        # returning/raising/recursing. Update this variable if necessary, and
        # leave `release_conn` constant throughout the function. That way, if
        # the function recurses, the original value of `release_conn` will be
        # passed down into the recursive call, and its value will be respected.
        #
        # See issue #651 [1] for details.
        #
        # [1] <https://github.com/urllib3/urllib3/issues/651>
        release_this_conn = release_conn

        http_tunnel_required = connection_requires_http_tunnel(
            self.proxy, self.proxy_config, destination_scheme
        )

        # Merge the proxy headers. Only done when not using HTTP CONNECT. We
        # have to copy the headers dict so we can safely change it without those
        # changes being reflected in anyone else's copy.
        if not http_tunnel_required:
            headers = headers.copy()  # type: ignore[attr-defined]
            headers.update(self.proxy_headers)  # type: ignore[union-attr]

        # Must keep the exception bound to a separate variable or else Python 3
        # complains about UnboundLocalError.
        err = None

        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False

        # Rewind body position, if needed. Record current position
        # for future rewinds in the event of a redirect/retry.
        body_pos = set_file_position(body, body_pos)

        try:
            # Request a connection from the queue.
            timeout_obj = self._get_timeout(timeout)
            conn = self._get_conn(timeout=pool_timeout)

            conn.timeout = timeout_obj.connect_timeout  # type: ignore[assignment]

            # Is this a closed/new connection that requires CONNECT tunnelling?
            if self.proxy is not None and http_tunnel_required and conn.is_closed:
                try:
                    self._prepare_proxy(conn)
                except (BaseSSLError, OSError, SocketTimeout) as e:
                    self._raise_timeout(
                        err=e, url=self.proxy.url, timeout_value=conn.timeout
                    )
                    raise

            # If we're going to release the connection in ``finally:``, then
            # the response doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = conn if not release_conn else None

            # Make the request on the HTTPConnection object

>           response = self._make_request(

                conn,
                method,
                url,
                timeout=timeout_obj,
                body=body,
                headers=headers,
                chunked=chunked,
                retries=retries,
                response_conn=response_conn,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:788:

---

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:493: in \_make_request
conn.request(
.venv/lib/python3.12/site-packages/urllib3/connection.py:500: in request
self.endheaders()
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1333: in endheaders
self.\_send_output(message_body, encode_chunked=encode_chunked)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1093: in \_send_output
self.send(msg)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1037: in send
self.connect()

---

self = <UnixHTTPConnection(host='localhost', port=80) at 0x10a8f87d0>

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

>       sock.connect(self.unix_socket)
>
> E FileNotFoundError: [Errno 2] No such file or directory

.venv/lib/python3.12/site-packages/docker/transport/unixconn.py:26: FileNotFoundError

During handling of the above exception, another exception occurred:

self = <docker.transport.unixconn.UnixHTTPAdapter object at 0x10a98fc50>, request = <PreparedRequest [GET]>, stream = False
timeout = Timeout(connect=60, read=60, total=None), verify = True, cert = None, proxies = OrderedDict()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:

>           resp = conn.urlopen(

                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

.venv/lib/python3.12/site-packages/requests/adapters.py:645:

---

.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:842: in urlopen
retries = retries.increment(
.venv/lib/python3.12/site-packages/urllib3/util/retry.py:498: in increment
raise reraise(type(error), error, \_stacktrace)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/urllib3/util/util.py:38: in reraise
raise value.with_traceback(tb)
.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:788: in urlopen
response = self.\_make_request(
.venv/lib/python3.12/site-packages/urllib3/connectionpool.py:493: in \_make_request
conn.request(
.venv/lib/python3.12/site-packages/urllib3/connection.py:500: in request
self.endheaders()
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1333: in endheaders
self.\_send_output(message_body, encode_chunked=encode_chunked)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1093: in \_send_output
self.send(msg)
/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/http/client.py:1037: in send
self.connect()

---

self = <UnixHTTPConnection(host='localhost', port=80) at 0x10a8f87d0>

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

>       sock.connect(self.unix_socket)
>
> E urllib3.exceptions.ProtocolError: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/docker/transport/unixconn.py:26: ProtocolError

During handling of the above exception, another exception occurred:

self = <docker.api.client.APIClient object at 0x10a98fec0>

    def _retrieve_server_version(self):
        try:

>           return self.version(api_version=False)["ApiVersion"]

                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.venv/lib/python3.12/site-packages/docker/api/client.py:223:

---

.venv/lib/python3.12/site-packages/docker/api/daemon.py:181: in version
return self.\_result(self.\_get(url), json=True)
^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/utils/decorators.py:44: in inner
return f(self, \*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/api/client.py:246: in \_get
return self.get(url, **self.\_set_request_timeout(kwargs))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:605: in get
return self.request("GET", url, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:592: in request
resp = self.send(prep, **send_kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/requests/sessions.py:706: in send
r = adapter.send(request, \*\*kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

---

self = <docker.transport.unixconn.UnixHTTPAdapter object at 0x10a98fc50>, request = <PreparedRequest [GET]>, stream = False
timeout = Timeout(connect=60, read=60, total=None), verify = True, cert = None, proxies = OrderedDict()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            resp = conn.urlopen(
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

        except (ProtocolError, OSError) as err:

>           raise ConnectionError(err, request=request)
>
> E requests.exceptions.ConnectionError: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/requests/adapters.py:660: ConnectionError

The above exception was the direct cause of the following exception:

    @pytest.fixture(scope="session")
    def postgres_url() -> AsyncIterator[str]:
        """Start a disposable Postgres and return an asyncpg URL."""

>       with PostgresContainer("postgres:16-alpine") as pg:

             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

app/tests/conftest.py:25:

---

.venv/lib/python3.12/site-packages/testcontainers/postgres/**init**.py:59: in **init**
super().**init**(image=image, **kwargs)
.venv/lib/python3.12/site-packages/testcontainers/core/container.py:86: in **init**
self.\_docker = DockerClient(**(docker_client_kw or {}))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/testcontainers/core/docker_client.py:73: in **init**
self.client = docker.from_env(**kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/client.py:94: in from_env
return cls(
.venv/lib/python3.12/site-packages/docker/client.py:45: in **init**
self.api = APIClient(\*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/docker/api/client.py:207: in **init**
self.\_version = self.\_retrieve_server_version()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

---

self = <docker.api.client.APIClient object at 0x10a98fec0>

    def _retrieve_server_version(self):
        try:
            return self.version(api_version=False)["ApiVersion"]
        except KeyError as ke:
            raise DockerException(
                'Invalid response from docker daemon: key "ApiVersion"'
                ' is missing.'
            ) from ke
        except Exception as e:

>           raise DockerException(

                f'Error while fetching server API version: {e}'
            ) from e

E docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

.venv/lib/python3.12/site-packages/docker/api/client.py:230: DockerException
============================================================== FAILURES ===============================================================
**********************\_\_\_\_********************** test_spider_parse_yields_gazette_item **********************\_\_\_\_**********************

    def test_spider_parse_yields_gazette_item():
        """Spider parses the fixture listing and yields one item with the correct
        gazette_number, gazette_date, and pdf_url.

        Sync test — spider.parse is a generator, no awaits needed.
        """
        listing_html = (FIXTURES_DIR / "gazette_listing.html").read_bytes()
        response = _build_fake_listing_response(
            listing_html,
            url="http://localhost/view/egz/egz_2026.html",
        )

        spider = GazetteSpider()
        items = list(spider.parse(response))

>       assert len(items) == 1, f"expected 1 item, got {len(items)}"
>
> E AssertionError: expected 1 item, got 0
> E assert 0 == 1
> E + where 0 = len([])

app/tests/integration/test_gazette_spider.py:87: AssertionError
======================================================= short test summary info =======================================================
FAILED app/tests/integration/test_gazette_spider.py::test_spider_parse_yields_gazette_item - AssertionError: expected 1 item, got 0
ERROR app/tests/integration/test_gazette_spider.py::test_insert_pipeline_creates_m1_regulations_row - docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file...
ERROR app/tests/integration/test_gazette_spider.py::test_insert_pipeline_is_idempotent_on_duplicate - docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file...
================================================ 1 failed, 1 passed, 2 errors in 0.84s ================================================
warning: `VIRTUAL_ENV=/Users/arqm7/Documents/Github Repos/xyz/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
2026-05-15T17:16:15 [scrapy.utils.log] INFO: Scrapy 2.15.2 started (bot: enigmatrix-m1-scraper)
2026-05-15T17:16:15 [scrapy.utils.log] INFO: Versions:
{'lxml': '6.1.0',
'libxml2': '2.14.6',
'cssselect': '1.4.0',
'parsel': '1.11.0',
'w3lib': '2.4.1',
'Twisted': '25.5.0',
'Python': '3.12.9 (v3.12.9:fdb81425a9a, Feb 4 2025, 12:21:36) [Clang 13.0.0 '
'(clang-1300.0.29.30)]',
'pyOpenSSL': '26.2.0 (OpenSSL 4.0.0 14 Apr 2026)',
'cryptography': '48.0.0',
'Platform': 'macOS-26.3-arm64-arm-64bit'}
2026-05-15T17:16:15 [scrapy.addons] INFO: Enabled addons:
[]
2026-05-15T17:16:15 [scrapy.middleware] INFO: Enabled extensions:
['scrapy.extensions.corestats.CoreStats',
'scrapy.extensions.logcount.LogCount',
'scrapy.extensions.memusage.MemoryUsage',
'scrapy.extensions.logstats.LogStats',
'scrapy.extensions.throttle.AutoThrottle']
2026-05-15T17:16:15 [scrapy.crawler] INFO: Overridden settings:
{'AUTOTHROTTLE_ENABLED': True,
'AUTOTHROTTLE_MAX_DELAY': 30,
'AUTOTHROTTLE_START_DELAY': 1,
'AUTOTHROTTLE_TARGET_CONCURRENCY': 2,
'BOT_NAME': 'enigmatrix-m1-scraper',
'COOKIES_ENABLED': False,
'DOWNLOAD_DELAY': 2,
'LOG_DATEFORMAT': '%Y-%m-%dT%H:%M:%S',
'LOG_LEVEL': 'INFO',
'NEWSPIDER_MODULE': 'scraper.spiders',
'RETRY_HTTP_CODES': [500, 503, 429],
'RETRY_TIMES': 5,
'ROBOTSTXT_OBEY': True,
'SPIDER_MODULES': ['scraper.spiders'],
'TELNETCONSOLE_ENABLED': False,
'USER_AGENT': 'EnigmatrixResearchBot/1.0 (+https://enigmatrix.lk/bot)'}
2026-05-15T17:16:15 [scrapy.middleware] INFO: Enabled downloader middlewares:
['scrapy.downloadermiddlewares.offsite.OffsiteMiddleware',
'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware',
'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware',
'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware',
'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware',
'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware',
'scrapy.downloadermiddlewares.retry.RetryMiddleware',
'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware',
'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware',
'scrapy.downloadermiddlewares.redirect.RedirectMiddleware',
'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware',
'scrapy.downloadermiddlewares.stats.DownloaderStats']
2026-05-15T17:16:15 [scrapy.middleware] INFO: Enabled spider middlewares:
['scrapy.spidermiddlewares.start.StartSpiderMiddleware',
'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware',
'scrapy.spidermiddlewares.referer.RefererMiddleware',
'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware',
'scrapy.spidermiddlewares.depth.DepthMiddleware']
2026-05-15T17:16:15 [scrapy.middleware] INFO: Enabled item pipelines:
['scraper.pipelines.PDFDownloadPipeline',
'scraper.pipelines.M1RegulationsInsertPipeline']
2026-05-15T17:16:15 [py.warnings] WARNING: /Users/arqm7/Documents/Github Repos/xyz/enigmatrix-backend/.venv/lib/python3.12/site-packages/scrapy/pipelines/**init**.py:49: ScrapyDeprecationWarning: PDFDownloadPipeline.process_item() requires a spider argument, this is deprecated and the argument will not be passed in future Scrapy versions. If you need to access the spider instance you can save the crawler instance passed to from_crawler() and use its spider attribute.
self.\_check_mw_method_spider_arg(pipe.process_item)

2026-05-15T17:16:15 [py.warnings] WARNING: /Users/arqm7/Documents/Github Repos/xyz/enigmatrix-backend/.venv/lib/python3.12/site-packages/scrapy/pipelines/**init**.py:49: ScrapyDeprecationWarning: M1RegulationsInsertPipeline.process_item() requires a spider argument, this is deprecated and the argument will not be passed in future Scrapy versions. If you need to access the spider instance you can save the crawler instance passed to from_crawler() and use its spider attribute.
self.\_check_mw_method_spider_arg(pipe.process_item)

2026-05-15T17:16:15 [scrapy.core.engine] INFO: Spider opened
2026-05-15T17:16:15 [scrapy.extensions.logstats] INFO: Crawled 0 pages (at 0 pages/min), scraped 0 items (at 0 items/min)
2026-05-15T17:17:08 [scrapy.core.engine] INFO: Closing spider (finished)
2026-05-15T17:17:08 [scrapy.statscollectors] INFO: Dumping Scrapy stats:
{'downloader/request_bytes': 504,
'downloader/request_count': 2,
'downloader/request_method_count/GET': 2,
'downloader/response_bytes': 638419,
'downloader/response_count': 2,
'downloader/response_status_count/200': 1,
'downloader/response_status_count/404': 1,
'elapsed_time_seconds': 52.944994,
'finish_reason': 'finished',
'finish_time': datetime.datetime(2026, 5, 15, 11, 47, 8, 772397, tzinfo=datetime.timezone.utc),
'items_per_minute': 0.0,
'log_count/INFO': 2,
'memusage/max': 110804992,
'memusage/startup': 110804992,
'response_received_count': 2,
'responses_per_minute': 2.3076923076923075,
'robotstxt/request_count': 1,
'robotstxt/response_count': 1,
'robotstxt/response_status_count/404': 1,
'scheduler/dequeued': 1,
'scheduler/dequeued/memory': 1,
'scheduler/enqueued': 1,
'scheduler/enqueued/memory': 1,
'start_time': datetime.datetime(2026, 5, 15, 11, 46, 15, 827403, tzinfo=datetime.timezone.utc)}
2026-05-15T17:17:08 [scrapy.core.engine] INFO: Spider closed (finished)
(.venv) arqm7@ARQMs-MacBook-Air enigmatrix-backend %
