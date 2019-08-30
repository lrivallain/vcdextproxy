# Main idea

A python based worker looking at multiple AMQP queues for incoming request for vCD Extensions:

* Support multiple queues subscriptions
* Can address multiple REST endpoint depending on extension
* 1 REST endpoint is a associated to 1 extension in vCD
* Will be later able to address some pre-checks like rights management


Example:

**vcdExtpProxy** (vET) subscribe to following queues:

* `lumext`
* `test`

When a message is sent to `lumext` queue:

1. A URI path check is made: is `/api/lumext` a correct API path for extension named **Lumext** ?
2. If valid, all fields of the request are converted to REST request (as headers or as body content)
3. REST endpoint handle the request as a standard REST one (with a lot of vCloud information...)
4. REST endpoint replies to **vET**
5. **vET** represent the reply as an AMQP reply message
