# Notifications de commande

## Modèle de traitement

Les e-mails métier sont enregistrés dans `OrderNotification` avant envoi. Le code d'envoi réserve l'état `sending` dans une transaction courte, effectue l'appel SMTP hors transaction, puis enregistre le résultat. Les messages acceptés par le prestataire passent en `sent`; les échecs sont conservés pour diagnostic et reprise.

Le statut `sent` signifie que le backend e-mail a accepté le message, pas que le destinataire l'a lu ni que le message a été placé dans sa boîte de réception.

## Commande de traitement

La commande Django suivante traite les messages disponibles, avec un lot maximal configurable :

```bash
python manage.py process_order_notifications --limit 50
```

Pour vérifier le nombre de messages qui seraient traités sans envoyer d'e-mail :

```bash
python manage.py process_order_notifications --dry-run
```

Les échecs utilisent un délai progressif avant une nouvelle tentative. Les tentatives `sending` devenues anciennes sont remises en file avec prudence. Après cinq tentatives, une intervention est nécessaire.

## Exploitation à prévoir

Un ordonnanceur externe devra exécuter périodiquement la commande dans l'environnement approprié. La configuration de cet ordonnanceur n'est pas incluse ici. Il faut surveiller le nombre de notifications en échec, les tentatives anciennes et la configuration SMTP.

Une interruption après acceptation du message par le prestataire, mais avant l'enregistrement du résultat, peut provoquer un doublon lors de la reprise. Le système fournit donc une livraison au moins une fois, pas une garantie stricte de livraison exactement une fois. Les événements métier doivent conserver des clés d'idempotence stables afin d'éviter de créer plusieurs notifications pour le même événement.
